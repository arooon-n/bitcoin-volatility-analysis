import org.apache.spark.sql.{SparkSession, DataFrame}
import org.apache.spark.sql.functions._
import org.yaml.snakeyaml.Yaml
import scala.collection.JavaConverters._
import java.io.FileInputStream
import java.util.{Map => JavaMap}

/**
 * Bitcoin Volatility Batch Analysis
 * 
 * Performs comprehensive batch analysis on historical Bitcoin data stored in HDFS.
 * Generates three types of analysis:
 * 
 * 1. Daily Statistics: Price and volatility aggregations by date
 * 2. Hourly Pattern: Average volatility by hour of day
 * 3. Volatility Spikes: Extreme volatility events (99th percentile)
 * 
 * All outputs are saved to HDFS in Parquet format for further analysis.
 */
object BatchAnalysis {
  
  /**
   * Load configuration from YAML file
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
   * Analysis 1: Daily Statistics
   * 
   * Aggregates price and volatility metrics by date.
   * Provides daily average, max, min prices and volatility measures.
   */
  def analyzeDailyStats(df: DataFrame, outputPath: String): Unit = {
    println("=" * 60)
    println("  ANALYSIS 1: Daily Statistics")
    println("=" * 60)
    println()
    
    val dailyStats = df
      .groupBy("date")
      .agg(
        avg("price").alias("avg_price"),
        max("price").alias("max_price"),
        min("price").alias("min_price"),
        avg("volatility_24h").alias("avg_vol"),
        max("volatility_24h").alias("max_vol"),
        min("volatility_24h").alias("min_vol"),
        stddev("volatility_24h").alias("std_vol"),
        sum("volume24h").alias("total_volume"),
        count("*").alias("record_count")
      )
      .orderBy("date")
    
    // Show sample results
    println("Sample Daily Statistics (most recent 10 days):")
    dailyStats.show(10, truncate = false)
    
    // Calculate total statistics
    val totalDays = dailyStats.count()
    println(s"Total days analyzed: $totalDays")
    println()
    
    // Write to HDFS
    println(s"Writing daily statistics to: $outputPath")
    dailyStats
      .write
      .mode("overwrite")
      .parquet(outputPath)
    
    println("✓ Daily statistics saved")
    println()
  }
  
  /**
   * Analysis 2: Hourly Volatility Pattern
   * 
   * Analyzes volatility patterns by hour of day to identify
   * when Bitcoin is most volatile (typically during high trading activity).
   */
  def analyzeHourlyPattern(df: DataFrame, outputPath: String): Unit = {
    println("=" * 60)
    println("  ANALYSIS 2: Hourly Volatility Pattern")
    println("=" * 60)
    println()
    
    val hourlyPattern = df
      .withColumn("hour_of_day", hour(col("event_time")))
      .groupBy("hour_of_day")
      .agg(
        avg("volatility_1h").alias("avg_vol_1h"),
        avg("volatility_24h").alias("avg_vol_24h"),
        count("*").alias("record_count")
      )
      .orderBy("hour_of_day")
    
    // Show all 24 hours
    println("Volatility by Hour of Day (UTC):")
    hourlyPattern.show(24, truncate = false)
    
    // Find peak volatility hour
    val peakHour = hourlyPattern
      .orderBy(desc("avg_vol_1h"))
      .first()
    
    println(s"Peak volatility hour: ${peakHour.getAs[Int]("hour_of_day")}:00 UTC")
    println(f"Average 1h volatility: ${peakHour.getAs[Double]("avg_vol_1h")}%.6f")
    println()
    
    // Write to HDFS
    println(s"Writing hourly pattern to: $outputPath")
    hourlyPattern
      .write
      .mode("overwrite")
      .parquet(outputPath)
    
    println("✓ Hourly pattern saved")
    println()
  }
  
  /**
   * Analysis 3: Volatility Spike Events
   * 
   * Identifies extreme volatility events (99th percentile).
   * These events are useful for risk management and understanding
   * market stress periods.
   */
  def analyzeVolatilitySpikes(df: DataFrame, outputPath: String): Unit = {
    println("=" * 60)
    println("  ANALYSIS 3: Volatility Spike Events")
    println("=" * 60)
    println()
    
    // Calculate 99th percentile threshold
    val threshold = df
      .stat
      .approxQuantile("volatility_24h", Array(0.99), 0.001)
      .head
    
    println(f"99th percentile volatility threshold: $threshold%.6f")
    println()
    
    // Filter spike events
    val spikes = df
      .filter(col("volatility_24h") > threshold)
      .select(
        col("datetime"),
        col("date"),
        col("price"),
        col("volatility_24h"),
        col("volume24h"),
        col("high24h"),
        col("low24h")
      )
      .orderBy(desc("volatility_24h"))
    
    val spikeCount = spikes.count()
    println(s"Total spike events identified: $spikeCount")
    println()
    
    // Show top 20 spikes
    println("Top 20 Volatility Spike Events:")
    spikes.show(20, truncate = false)
    println()
    
    // Write to HDFS
    println(s"Writing volatility spikes to: $outputPath")
    spikes
      .write
      .mode("overwrite")
      .parquet(outputPath)
    
    println("✓ Volatility spikes saved")
    println()
  }
  
  /**
   * Main entry point
   */
  def main(args: Array[String]): Unit = {
    println()
    println("=" * 60)
    println("  Bitcoin Volatility Batch Analysis")
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
        Map.empty[String, Any]
    }
    
    // Extract configuration values
    val hdfsNamenode = getConfigValue(config, "hdfs", "namenode")
    val hdfsHistoricalPath = getConfigValue(config, "hdfs", "paths", "historical")
    val hdfsAnalysisPath = getConfigValue(config, "hdfs", "paths", "analysis")
    val appName = "BitcoinBatchAnalysis"
    val sparkMaster = getConfigValue(config, "spark", "master")
    val shufflePartitions = getConfigValue(config, "spark", "shuffle_partitions")
    
    println(s"✓ HDFS Namenode: $hdfsNamenode")
    println(s"✓ Input Path: $hdfsHistoricalPath")
    println(s"✓ Output Path: $hdfsAnalysisPath")
    println()
    
    // Create Spark Session
    val spark = SparkSession
      .builder()
      .appName(appName)
      .master(sparkMaster)
      .config("spark.sql.shuffle.partitions", shufflePartitions)
      .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    println("✓ Spark Session created")
    println()
    
    try {
      // Load data from HDFS
      println("Loading historical data from HDFS...")
      val inputPath = s"$hdfsNamenode$hdfsHistoricalPath"
      
      val df = spark
        .read
        .parquet(inputPath)
      
      // Cache the DataFrame as we'll use it multiple times
      df.cache()
      
      val totalRecords = df.count()
      println(s"✓ Loaded $totalRecords records from HDFS")
      println()
      
      // Verify required columns exist
      val requiredColumns = Set("date", "datetime", "price", "volatility_24h", 
                                 "volatility_1h", "event_time", "volume24h", 
                                 "high24h", "low24h")
      val availableColumns = df.columns.toSet
      
      if (!requiredColumns.subsetOf(availableColumns)) {
        val missing = requiredColumns.diff(availableColumns)
        println(s"ERROR: Missing required columns: ${missing.mkString(", ")}")
        println("Please ensure the streaming job has run and generated complete data.")
        System.exit(1)
      }
      
      // Run analyses
      val analysisBasePath = s"$hdfsNamenode$hdfsAnalysisPath"
      
      // Analysis 1: Daily Statistics
      analyzeDailyStats(df, s"$analysisBasePath/daily_stats")
      
      // Analysis 2: Hourly Pattern
      analyzeHourlyPattern(df, s"$analysisBasePath/hourly_pattern")
      
      // Analysis 3: Volatility Spikes
      analyzeVolatilitySpikes(df, s"$analysisBasePath/volatility_spikes")
      
      // Final summary
      println("=" * 60)
      println("  ✓ BATCH ANALYSIS COMPLETE")
      println("=" * 60)
      println()
      println("Summary:")
      println(s"  • Total records analyzed: $totalRecords")
      println(s"  • Analyses generated: 3")
      println(s"  • Output location: $analysisBasePath")
      println()
      println("Output directories:")
      println(s"  1. $analysisBasePath/daily_stats")
      println(s"  2. $analysisBasePath/hourly_pattern")
      println(s"  3. $analysisBasePath/volatility_spikes")
      println()
      println("To view results, use:")
      println(s"  docker exec namenode hdfs dfs -ls -R $hdfsAnalysisPath")
      println()
      
    } catch {
      case e: Exception =>
        println()
        println(s"ERROR: ${e.getMessage}")
        e.printStackTrace()
    } finally {
      println("Stopping Spark Session...")
      spark.stop()
      println("✓ Batch analysis session stopped")
      println()
    }
  }
}
