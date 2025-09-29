#!/bin/bash
# Deploy CallWaiting.ai TTS Service to RunPod Pod

set -e

echo "🚀 Deploying CallWaiting.ai TTS Service to RunPod Pod"
echo "=================================================="

# Configuration
IMAGE_NAME="callwaiting-tts-service"
REGISTRY="your-registry.com"  # Replace with your container registry
FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}:latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📋 Deployment Configuration:${NC}"
echo "  Image: ${FULL_IMAGE_NAME}"
echo "  Pod: RTX 2000 Ada x1"
echo "  Memory: 31 GB"
echo "  Volume: 50 GB at /workspace"
echo ""

# Step 1: Build Docker image
echo -e "${YELLOW}🔨 Step 1: Building Docker image...${NC}"
docker build -f Dockerfile.runpod.pod -t ${IMAGE_NAME} .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker image built successfully${NC}"
else
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi

# Step 2: Tag for registry
echo -e "${YELLOW}🏷️  Step 2: Tagging image for registry...${NC}"
docker tag ${IMAGE_NAME} ${FULL_IMAGE_NAME}

# Step 3: Push to registry (optional - you can also use RunPod's built-in registry)
echo -e "${YELLOW}📤 Step 3: Pushing to registry...${NC}"
echo -e "${BLUE}Note: You can skip this step and use RunPod's built-in registry${NC}"
read -p "Push to registry? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker push ${FULL_IMAGE_NAME}
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Image pushed to registry${NC}"
    else
        echo -e "${RED}❌ Push failed${NC}"
        exit 1
    fi
else
    echo -e "${BLUE}⏭️  Skipping registry push${NC}"
fi

# Step 4: Create RunPod template configuration
echo -e "${YELLOW}📝 Step 4: Creating RunPod template configuration...${NC}"
cat > runpod_template_config.json << EOF
{
  "name": "callwaiting-tts-service",
  "image": "${FULL_IMAGE_NAME}",
  "containerDiskSizeGb": 30,
  "volumeInGb": 50,
  "volumeMountPath": "/workspace",
  "ports": "8000/http",
  "env": [
    {
      "key": "PYTHONPATH",
      "value": "/workspace"
    },
    {
      "key": "PYTHONUNBUFFERED",
      "value": "1"
    },
    {
      "key": "HOST",
      "value": "0.0.0.0"
    },
    {
      "key": "PORT",
      "value": "8000"
    }
  ],
  "startJupyter": false,
  "startSsh": true,
  "runPodMaxMemory": 31,
  "runPodMaxVcpu": 6
}
EOF

echo -e "${GREEN}✅ Template configuration created: runpod_template_config.json${NC}"

# Step 5: Instructions for RunPod deployment
echo -e "${YELLOW}📋 Step 5: RunPod Deployment Instructions${NC}"
echo ""
echo -e "${BLUE}To deploy your TTS service to RunPod:${NC}"
echo ""
echo "1. Go to RunPod Dashboard → Templates"
echo "2. Create New Template with these settings:"
echo "   - Name: callwaiting-tts-service"
echo "   - Container Image: ${FULL_IMAGE_NAME}"
echo "   - Container Disk: 30 GB"
echo "   - Volume: 50 GB at /workspace"
echo "   - Ports: 8000/http"
echo "   - Environment Variables:"
echo "     - PYTHONPATH=/workspace"
echo "     - PYTHONUNBUFFERED=1"
echo "     - HOST=0.0.0.0"
echo "     - PORT=8000"
echo ""
echo "3. Go to RunPod Dashboard → Pods"
echo "4. Deploy New Pod:"
echo "   - Select your RTX 2000 Ada pod"
echo "   - Choose the callwaiting-tts-service template"
echo "   - Deploy"
echo ""
echo "5. Access your TTS service:"
echo "   - HTTP endpoint: http://your-pod-ip:8000"
echo "   - Health check: http://your-pod-ip:8000/v1/health"
echo "   - API docs: http://your-pod-ip:8000/docs"
echo ""

# Step 6: Test configuration
echo -e "${YELLOW}🧪 Step 6: Testing local configuration...${NC}"
echo "Testing Edge TTS installation..."
python3 -c "
import edge_tts
print('✅ Edge TTS available')
print('✅ Ready for RunPod deployment')
" 2>/dev/null || echo -e "${RED}❌ Edge TTS not available locally${NC}"

echo ""
echo -e "${GREEN}🎉 Deployment preparation complete!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Follow the RunPod deployment instructions above"
echo "2. Test your deployed service"
echo "3. Update your client configuration with the pod IP"
echo ""
echo -e "${YELLOW}💡 Pro tip: Use RunPod's built-in registry to avoid external registry costs${NC}"
