terraform {
  backend "s3" {
    key    = "GetChofuCityGabageSkill.tfstate"
    region = "ap-northeast-1"
  }
}
