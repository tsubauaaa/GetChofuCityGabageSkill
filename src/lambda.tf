resource "aws_lambda_function" "GetChofuCityGabageSkill" {
  filename         = "GetChofuCityGabageSkill.zip"
  function_name    = "GetChofuCityGabageSkill"
  role             = "arn:aws:iam::905774158693:role/tsubauaaa-lambda-role"
  handler          = "GetChofuCityGabageSkill.lambda_handler"
  source_code_hash = "${base64sha256(file("GetChofuCityGabageSkill.zip"))}"
  runtime          = "python3.6"
  timeout          = 300
  publish          = true
}
