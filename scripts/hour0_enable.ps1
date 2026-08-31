# tmc-gate hour-0 enablement (run AFTER billing is open)
# Usage:  .\scripts\hour0_enable.ps1 -ProjectId "your-project-id"
# Does not mint service-account JSON keys. Does not deploy Cloud Run.

param(
  [Parameter(Mandatory = $true)][string]$ProjectId,
  [string]$Region = "us-central1"
)

$ErrorActionPreference = "Stop"
gcloud config set project $ProjectId

Write-Host "Enabling APIs on $ProjectId ..."
gcloud services enable `
  earthengine.googleapis.com `
  bigquery.googleapis.com `
  pubsub.googleapis.com `
  modelarmor.googleapis.com `
  cloudfunctions.googleapis.com `
  firestore.googleapis.com `
  secretmanager.googleapis.com `
  storage.googleapis.com `
  aiplatform.googleapis.com `
  cloudbuild.googleapis.com `
  artifactregistry.googleapis.com `
  eventarc.googleapis.com `
  run.googleapis.com
# run.googleapis.com is often a dependency of Functions 2nd gen.
# We still MUST NOT deploy a Cloud Run *service* as the product host.

Write-Host ""
Write-Host "Register Earth Engine (browser):"
Write-Host "  https://code.earthengine.google.com/register?project=$ProjectId"
Write-Host "Choose noncommercial / unpaid for this hackathon fixture."
Write-Host ""
Write-Host "Create Gemini secret (paste key when prompted, do not echo it into chat):"
Write-Host "  gcloud secrets create gemini-api-key --data-file=-"
Write-Host ""
Write-Host "If Earth Engine or Model Armor cannot enable: print the failed A letter in README."
Write-Host "Do not silently skip. Do not close on intersect-only. Do not deploy .run.app as the host."
