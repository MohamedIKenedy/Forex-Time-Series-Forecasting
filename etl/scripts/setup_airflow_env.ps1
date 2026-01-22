param(
    [string]$S3Bucket = "my-bucket",
    [string]$S3Prefix = "forex",
    [string]$PgConnId = "postgres_default",
    [string]$TargetTable = "public.forex_prices",
    [string]$SnsTopicArn = "",
    [string]$AwsConnId = "aws_default",
    [string]$SparkConnId = "spark_default",
    [string]$EtlTicker = "EURUSD=X",
    [string]$AlertEmails = ""
)

Write-Host "Setting Airflow Variables..."
airflow variables set S3_BUCKET $S3Bucket
airflow variables set S3_PREFIX $S3Prefix
airflow variables set PG_CONN_ID $PgConnId
airflow variables set TARGET_TABLE $TargetTable
airflow variables set AWS_CONN_ID $AwsConnId
airflow variables set SPARK_CONN_ID $SparkConnId
airflow variables set ETL_TICKER $EtlTicker
if ($SnsTopicArn -ne "") {
    airflow variables set SNS_TOPIC_ARN $SnsTopicArn
}
if ($AlertEmails -ne "") {
    airflow variables set ALERT_EMAILS $AlertEmails
}

Write-Host "Ensuring Postgres connection exists (placeholder)..."
# Check if connection exists
$exists = (airflow connections get $PgConnId -o json) 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating placeholder Postgres connection ($PgConnId). Update credentials in Airflow UI or via CLI."
    airflow connections add $PgConnId --conn-uri "postgresql://user:password@hostname:5432/dbname"
} else {
    Write-Host "Connection $PgConnId already exists."
}

Write-Host "Airflow variables and connection setup complete."
