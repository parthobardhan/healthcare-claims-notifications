#!/bin/bash
set -e

echo "Building and deploying Healthcare Claims Lambda functions..."

cd backend
pip install -r lambda-requirements.txt -t ./
cd ..

sam build
sam deploy --guided

echo "Deployment complete!"
echo "Remember to:"
echo "1. Update frontend API endpoints to use the Lambda URLs"
echo "2. Configure MongoDB Atlas to allow Lambda IP ranges"
echo "3. Test all endpoints with curl commands"
