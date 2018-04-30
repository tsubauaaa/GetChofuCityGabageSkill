resource "aws_lambda_function" "GetChofuCityGabageSkill" {
  filename         = "GetChofuCityGabageSkill.zip"
  function_name    = "GetChofuCityGabageSkill"
  role             = "arn:aws:iam::${var.aws_account_id}:role/tsubauaaa-lambda-role"
  handler          = "GetChofuCityGabageSkill.lambda_handler"
  source_code_hash = "${base64sha256(file("GetChofuCityGabageSkill.zip"))}"
  runtime          = "python3.6"
  timeout          = 300
  publish          = true

  environment {
    variables = {
      BUCKET_NAME = "${var.s3_bucket_name}"
      TZ          = "Asia/Tokyo"
    }
  }
}
