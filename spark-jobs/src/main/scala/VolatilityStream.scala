import org.apache.spark.sql.{SparkSession, DataFrame}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.streaming.Trigger
import org.yaml.snakeyaml.Yaml
import scala.io.Source
import scala.collection.JavaConverters._
import java.io.FileInputStream
import java.util.{Map => JavaMap}

/**
 * Bitcoin Volatility Stream Processing
 * 
 * Reads Bitcoin price data from Kafka, computes real-time volatility metrics,
 * and writes to two sinks:
 * 1. HDFS (Parquet format, partitioned by date) for historical analysis
 * 2. Local filesystem (JSON format) for dashboard consumption
 * 
 * Volatility metrics computed:
 * - Log returns: ln(P_t / P_t-1)
 * - Rolling 1-hour volatility: stddev of log returns over 1-hour window
 * - Rolling 24-hour volatility: stddev of log returns over 24-hour window
 * - Moving averages: 1-hour and 24-hour price moving averages
 */
object VolatilityStream {
  
  /**
   * Load configuration from YAML file
   * 
   * @param configPath Path to config.yaml
   * @return Map of configuration values
   */
  def loadConfig(configPath: String): Map[String, Any] = {
    val yaml = new Yaml()
    val inputStream = new FileInputStream(configPath)
    try {
      val config = yaml.load(inputStream).asInstanceOf[JavaMap[String, Any]]
      convertJavaMapToScala(config).asInstanceOf[Map[String, Any]]
    } finally {
      inputStream.close()
    }
  }
  
  /**
   * Recursively convert Java Map to Scala Map
   */
  def convertJavaMapToScala(javaMap: Any): Any = {
    javaMap match {
      case m: JavaMap[_, _] =>
        m.asScala.toMap.map { case (k, v) =>
          k.toString -> convertJavaMapToScala(v)
        }
      case other => other
    }
  }
  
  /**
   * Extract nested configuration value
   */
  def getConfigValue(config: Map[String, Any], path: String*): String = {
    path.foldLeft(config: Any) { case (current, key) =>
      current.asInstanceOf[Map[String, Any]](key)
    }.toString
  }
  
  /**
   * Define Kafka source schema for Bitcoin price data
   */
  def getPriceSchema: StructType = {
    StructType(Seq(
      StructField("timestamp", LongType, nullable = false),
      StructField("datetime", StringType, nullable = true),
      StructField("price", DoubleType, nullable = false),
      StructField("open24h", DoubleType, nullable = true),
      StructField("high24h", DoubleType, nullable = true),
      StructField("low24h", DoubleType, nullable = true),
      StructField("volume24h", DoubleType, nullable = true),
      StructField("volumeto24h", DoubleType, nullable = true),
      StructField("change24h", DoubleType, nullable = true),
      StructField("changepct24h", DoubleType, nullable = true),
      StructField("market_cap", DoubleType, nullable = true),
      StructField("supply", DoubleType, nullable = true)
    ))
  }
  
  /**
   * Add volatility metrics to the DataFrame
   * 
   * @param df Input DataFrame with price data
   * @return DataFrame with added volatility columns
   */
  def addVolatilityMetrics(df: DataFrame): DataFrame = {
    // Window specification ordered by timestamp
    val windowSpec = Window.orderBy("timestamp")
    
    // Previous price for calculating log returns
    val prevPriceCol = lag(col("price"), 1).over(windowSpec)
    
    // Log return: ln(price_t / price_t-1)
    val logReturnCol = when(
      prevPriceCol.isNotNull && prevPriceCol > 0,
      log(col("price") / prevPriceCol)
    ).otherwise(lit(0.0))
    
    // Window specifications for rolling calculations
    // 1 hour = 3600 seconds, 24 hours = 86400 seconds
    val window1h = Window
      .orderBy(col("timestamp").cast(LongType))
      .rangeBetween(-3600, 0)
    
    val window24h = Window
      .orderBy(col("timestamp").cast(LongType))
      .rangeBetween(-86400, 0)
    
    // Add columns step by step
    df
      .withColumn("prev_price", prevPriceCol)
      .withColumn("log_return", logReturnCol)
      .withColumn("volatility_1h", 
        coalesce(stddev(col("log_return")).over(window1h), lit(0.0)))
      .withColumn("volatility_24h", 
        coalesce(stddev(col("log_return")).over(window24h), lit(0.0)))
      .withColumn("price_ma_1h", 
        coalesce(avg(col("price")).over(window1h), col("price")))
      .withColumn("price_ma_24h", 
        coalesce(avg(col("price")).over(window24h), col("price")))
      .withColumn("price_change_pct",
        when(
          col("prev_price").isNotNull && col("prev_price") > 0,
          ((col("price") - col("prev_price")) / col("prev_price")) * 100
        ).otherwise(lit(0.0)))
      .drop("prev_price")  // Drop intermediate column
  }
  
  /**
   * Main entry point
   */
  def main(args: Array[String]): Unit = {
    println("=" * 60)
    println("  Bitcoin Volatility Stream Processing")
    println("=" * 60)
    println()
    
    // Load configuration
    val configPath = if (args.length > 0) args(0) else "../config/config.yaml"
    println(s"Loading configuration from: $configPath")
    
    val config = try {
      loadConfig(configPath)
    } catch {
      case e: Exception =>
        println(s"ERROR: Failed to load configuration: ${e.getMessage}")
        System.exit(1)
        Map.empty[String, Any]  // Never reached, but needed for type checker
    }
    
    // Extract configuration values
    val kafkaBootstrapServers = getConfigValue(config, "kafka", "internal_bootstrap_servers")
    val kafkaTopic = getConfigValue(config, "kafka", "topic_prices")
    val hdfsNamenode = getConfigValue(config, "hdfs", "namenode")
    val hdfsHistoricalPath = getConfigValue(config, "hdfs", "paths", "historical")
    val hdfsCheckpointStream = getConfigValue(config, "hdfs", "paths", "checkpoints_stream")
    val hdfsCheckpointLatest = getConfigValue(config, "hdfs", "paths", "checkpoints_latest")
    val appName = getConfigValue(config, "spark", "app_name")
    val sparkMaster = getConfigValue(config, "spark", "master")
    val shufflePartitions = getConfigValue(config, "spark", "shuffle_partitions")
    val localDataPath = getConfigValue(config, "dashboard", "local_data_path")
    
    println(s"✓ Kafka Bootstrap Servers: $kafkaBootstrapServers")
    println(s"✓ Kafka Topic: $kafkaTopic")
    println(s"✓ HDFS Namenode: $hdfsNamenode")
    println(s"✓ Local Data Path: $localDataPath")
    println()
    
    // Create Spark Session
    val spark = SparkSession
      .builder()
      .appName(appName)
      .master(sparkMaster)
      .config("spark.sql.shuffle.partitions", shufflePartitions)
      .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true")
      .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    println("✓ Spark Session created")
    println()
    
    try {
      // Read from Kafka
      println("Connecting to Kafka stream...")
      val kafkaStream = spark
        .readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", kafkaBootstrapServers)
        .option("subscribe", kafkaTopic)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
      
      println("✓ Connected to Kafka stream")
      println()
      
      // Parse JSON from Kafka value
      val schema = getPriceSchema
      val parsedStream = kafkaStream
        .select(from_json(col("value").cast(StringType), schema).as("parsed"))
        .select("parsed.*")
        .withColumn("event_time", col("timestamp").cast(TimestampType))
        .withColumn("date", to_date(col("event_time")))

      // Add volatility metrics
      println("Computing volatility metrics...")
      println("✓ Volatility metrics configured")
      println()

      // Dashboard output columns
      val dashboardCols = Seq(
        "timestamp", "datetime", "event_time", "price",
        "log_return", "volatility_1h", "volatility_24h",
        "price_ma_1h", "price_ma_24h", "price_change_pct",
        "volume24h", "high24h", "low24h"
      )

      // Single foreachBatch query: apply windowed metrics on each static micro-batch
      // and write to both HDFS and local JSON sinks.
      println("Starting sinks (HDFS Parquet + local JSON)...")
      val query = parsedStream
        .writeStream
        .foreachBatch { (batchDF: org.apache.spark.sql.DataFrame, batchId: Long) =>
          if (!batchDF.isEmpty) {
            val withMetrics = addVolatilityMetrics(batchDF)

            // Sink 1: HDFS Parquet partitioned by date
            withMetrics
              .write
              .format("parquet")
              .mode("append")
              .partitionBy("date")
              .save(s"$hdfsNamenode$hdfsHistoricalPath")

            // Sink 2: Local JSON for dashboard
            withMetrics
              .select(dashboardCols.map(col): _*)
              .write
              .format("json")
              .mode("append")
              .save(localDataPath)
          }
        }
        .option("checkpointLocation", s"$hdfsNamenode$hdfsCheckpointStream")
        .trigger(Trigger.ProcessingTime("30 seconds"))
        .start()

      println(s"✓ HDFS sink: $hdfsNamenode$hdfsHistoricalPath")
      println(s"✓ Local sink: $localDataPath")
      println()
      
      // Print startup summary
      println("=" * 60)
      println("  Streaming Pipeline Active")
      println("=" * 60)
      println("HDFS Output:")
      println(s"  Path: $hdfsNamenode$hdfsHistoricalPath")
      println(s"  Format: Parquet (partitioned by date)")
      println(s"  Trigger: 30 seconds")
      println()
      println("Dashboard Output:")
      println(s"  Path: $localDataPath")
      println(s"  Format: JSON")
      println(s"  Trigger: 10 seconds")
      println()
      println("Metrics computed:")
      println("  • Log returns")
      println("  • 1-hour rolling volatility")
      println("  • 24-hour rolling volatility")
      println("  • 1-hour price moving average")
      println("  • 24-hour price moving average")
      println()
      println("Press Ctrl+C to stop the stream")
      println("=" * 60)
      println()
      
      // Wait for termination
      query.awaitTermination()
      
    } catch {
      case e: Exception =>
        println()
        println(s"ERROR: ${e.getMessage}")
        e.printStackTrace()
    } finally {
      println()
      println("Stopping Spark Session...")
      spark.stop()
      println("✓ Stream processing stopped")
    }
  }
}
