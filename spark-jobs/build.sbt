name := "bitcoin-volatility"

version := "1.0"

scalaVersion := "2.12.18"

libraryDependencies ++= Seq(
  "org.apache.spark" %% "spark-core"               % "3.5.8" % "provided",
  "org.apache.spark" %% "spark-sql"                % "3.5.8" % "provided",
  "org.apache.spark" %% "spark-sql-kafka-0-10"     % "3.5.8",
  "org.yaml"          % "snakeyaml"                % "1.33"
)

// Assembly settings for creating fat JAR
assembly / assemblyMergeStrategy := {
  case PathList("META-INF", "services", xs @ _*) => MergeStrategy.concat
  case PathList("META-INF", xs @ _*) => MergeStrategy.discard
  case x if x.endsWith("module-info.class") => MergeStrategy.discard
  case "reference.conf" => MergeStrategy.concat
  case _ => MergeStrategy.first
}

// Set main class
assembly / mainClass := Some("VolatilityStream")

// JAR name
assembly / assemblyJarName := "bitcoin-volatility-assembly-1.0.jar"
