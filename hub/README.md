# AstraFlow Hub

Hub hosts a public catalog for node packages and workflows.

## Structure
- docs/openapi.yaml: Hub API specification
- scripts/generate_hub_api.py: OpenAPI generator wrapper for hub/api
- web: Vue 3 + Element Plus front-end
- api: Generated FastAPI server stubs (created by the generator)

## Common tasks

Generate Hub API stubs:

python hub\scripts\generate_hub_api.py

Run Hub web app:

cd hub\web
npm install
npm run dev

Build Hub web app:

npm run build
