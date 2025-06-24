#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Configuration
ENVIRONMENT=${ENVIRONMENT:-production}
DOMAIN=${DOMAIN:-marketentropy.dev}
REGISTRY=${REGISTRY:-ghcr.io/developer-2046/market-entropy}
CLUSTER_NAME=${CLUSTER_NAME:-marketentropy-prod}
REGION=${REGION:-us-west-2}

log "🚀 Deploying MarketEntropy to ${ENVIRONMENT} environment"

# Check prerequisites
check_prerequisites() {
    log "🔍 Checking prerequisites..."
    
    # Check if required tools are installed
    command -v docker >/dev/null 2>&1 || error "Docker is required but not installed"
    command -v kubectl >/dev/null 2>&1 || error "kubectl is required but not installed"
    command -v aws >/dev/null 2>&1 || error "AWS CLI is required but not installed"
    command -v eksctl >/dev/null 2>&1 || error "eksctl is required but not installed"
    
    # Check if Docker is running
    docker info >/dev/null 2>&1 || error "Docker is not running"
    
    # Check AWS credentials
    aws sts get-caller-identity >/dev/null 2>&1 || error "AWS credentials not configured"
    
    success "Prerequisites check passed"
}

# Generate secure passwords
generate_secrets() {
    log "🔐 Generating secure secrets..."
    
    export DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    export REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    export JWT_SECRET=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-50)
    
    # Prompt for API key if not set
    if [ -z "$ALPHA_VANTAGE_API_KEY" ]; then
        echo -n "Enter your Alpha Vantage API key: "
        read -s ALPHA_VANTAGE_API_KEY
        echo
        export ALPHA_VANTAGE_API_KEY
    fi
    
    success "Secrets generated"
}

# Build and push Docker images
build_and_push() {
    log "📦 Building and pushing Docker images..."
    
    # Build images
    log "Building API image..."
    docker build -t ${REGISTRY}/api:latest -f Dockerfile.api .
    
    log "Building worker image..."
    docker build -t ${REGISTRY}/worker:latest -f Dockerfile.worker .
    
    log "Building frontend image..."
    docker build -t ${REGISTRY}/frontend:latest -f frontend/Dockerfile frontend/
    
    # Tag with commit hash for versioning
    COMMIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    docker tag ${REGISTRY}/api:latest ${REGISTRY}/api:${COMMIT_HASH}
    docker tag ${REGISTRY}/worker:latest ${REGISTRY}/worker:${COMMIT_HASH}
    docker tag ${REGISTRY}/frontend:latest ${REGISTRY}/frontend:${COMMIT_HASH}
    
    # Push to registry
    log "Pushing images to registry..."
    docker push ${REGISTRY}/api:latest
    docker push ${REGISTRY}/api:${COMMIT_HASH}
    docker push ${REGISTRY}/worker:latest
    docker push ${REGISTRY}/worker:${COMMIT_HASH}
    docker push ${REGISTRY}/frontend:latest
    docker push ${REGISTRY}/frontend:${COMMIT_HASH}
    
    success "Images built and pushed"
}

# Create EKS cluster if it doesn't exist
create_cluster() {
    log "☁️ Setting up EKS cluster..."
    
    # Check if cluster exists
    if eksctl get cluster --name=${CLUSTER_NAME} --region=${REGION} >/dev/null 2>&1; then
        warn "Cluster ${CLUSTER_NAME} already exists, skipping creation"
    else
        log "Creating EKS cluster ${CLUSTER_NAME}..."
        
        # Create cluster with optimized configuration
        eksctl create cluster \
            --name=${CLUSTER_NAME} \
            --region=${REGION} \
            --nodes=3 \
            --nodes-min=2 \
            --nodes-max=10 \
            --node-type=t3.medium \
            --managed \
            --with-oidc \
            --ssh-access \
            --ssh-public-key=~/.ssh/id_rsa.pub \
            --full-ecr-access \
            --asg-access \
            --external-dns-access \
            --appmesh-access \
            --alb-ingress-access
        
        success "EKS cluster created"
    fi
    
    # Update kubectl config
    aws eks update-kubeconfig --region ${REGION} --name ${CLUSTER_NAME}
    success "kubectl configured"
}

# Install cluster add-ons
install_addons() {
    log "🔧 Installing cluster add-ons..."
    
    # Install AWS Load Balancer Controller
    log "Installing AWS Load Balancer Controller..."
    kubectl apply -f https://github.com/kubernetes-sigs/aws-load-balancer-controller/releases/download/v2.7.2/v2_7_2_full.yaml
    
    # Install ingress-nginx
    log "Installing ingress-nginx..."
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/aws/deploy.yaml
    
    # Install cert-manager for SSL
    log "Installing cert-manager..."
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
    
    # Install metrics server
    log "Installing metrics server..."
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    
    # Wait for deployments to be ready
    log "Waiting for add-ons to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/ingress-nginx-controller -n ingress-nginx
    kubectl wait --for=condition=available --timeout=300s deployment/cert-manager -n cert-manager
    
    success "Add-ons installed"
}

# Setup monitoring
setup_monitoring() {
    log "📊 Setting up monitoring..."
    
    # Install Prometheus and Grafana using Helm
    log "Installing Helm..."
    curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
    
    log "Adding Prometheus Helm repo..."
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    log "Installing Prometheus stack..."
    helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
        --namespace monitoring \
        --create-namespace \
        --set prometheus.prometheusSpec.retention=30d \
        --set grafana.adminPassword="$(echo $DB_PASSWORD | head -c 16)" \
        --wait
    
    # Apply custom Grafana dashboards
    if [ -f "monitoring/grafana-dashboards.yaml" ]; then
        kubectl apply -f monitoring/grafana-dashboards.yaml
    fi
    
    success "Monitoring setup complete"
}

# Create Kubernetes secrets
create_secrets() {
    log "🔐 Creating Kubernetes secrets..."
    
    # Create namespace
    kubectl create namespace market-entropy --dry-run=client -o yaml | kubectl apply -f -
    
    # Database credentials
    kubectl create secret generic db-secret \
        --namespace=market-entropy \
        --from-literal=password="${DB_PASSWORD}" \
        --from-literal=url="postgresql://entropy_user:${DB_PASSWORD}@marketentropy-db.cluster-${REGION}.rds.amazonaws.com:5432/marketentropy" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # API keys
    kubectl create secret generic api-keys \
        --namespace=market-entropy \
        --from-literal=alpha-vantage="${ALPHA_VANTAGE_API_KEY}" \
        --from-literal=jwt-secret="${JWT_SECRET}" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Redis password
    kubectl create secret generic redis-secret \
        --namespace=market-entropy \
        --from-literal=password="${REDIS_PASSWORD}" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    success "Secrets created"
}

# Deploy application
deploy_application() {
    log "🚀 Deploying MarketEntropy application..."
    
    # Update image tags in Kubernetes manifests
    find k8s/ -name "*.yaml" -exec sed -i.bak "s|your-registry.com/market-entropy|${REGISTRY}|g" {} \;
    find k8s/ -name "*.yaml" -exec sed -i.bak "s|:latest|:${COMMIT_HASH:-latest}|g" {} \;
    
    # Apply Kubernetes manifests
    kubectl apply -f k8s/
    
    # Wait for deployments
    log "Waiting for deployments to be ready..."
    kubectl wait --for=condition=available --timeout=600s deployment/market-entropy-api -n market-entropy
    kubectl wait --for=condition=available --timeout=600s deployment/market-entropy-worker -n market-entropy
    kubectl wait --for=condition=available --timeout=600s deployment/market-entropy-frontend -n market-entropy
    
    success "Application deployed"
}

# Setup SSL and domain
setup_ssl() {
    log "🔒 Setting up SSL certificate..."
    
    # Create ClusterIssuer for Let's Encrypt
    cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@${DOMAIN}
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
    
    success "SSL configured"
}

# Get deployment info
get_deployment_info() {
    log "📡 Getting deployment information..."
    
    # Get load balancer IP/hostname
    LB_HOST=$(kubectl get service ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "pending")
    LB_IP=$(kubectl get service ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    
    # Get Grafana password
    GRAFANA_PASSWORD=$(kubectl get secret prometheus-grafana -n monitoring -o jsonpath="{.data.admin-password}" | base64 --decode 2>/dev/null || echo "unknown")
    
    echo ""
    echo "🎉 MarketEntropy Deployment Complete!"
    echo "============================================="
    echo ""
    echo "📡 Load Balancer: ${LB_HOST}${LB_IP:+ / ${LB_IP}}"
    echo "🌐 Domain: https://${DOMAIN}"
    echo "📊 Grafana: https://grafana.${DOMAIN}"
    echo "🔑 Grafana Password: ${GRAFANA_PASSWORD}"
    echo ""
    echo "📝 Next Steps:"
    echo "1. Update your DNS to point ${DOMAIN} to ${LB_HOST:-${LB_IP}}"
    echo "2. Wait for SSL certificate to be issued (may take a few minutes)"
    echo "3. Access your dashboard at https://${DOMAIN}"
    echo ""
    echo "🔧 Useful Commands:"
    echo "  kubectl get pods -n market-entropy"
    echo "  kubectl logs -f deployment/market-entropy-api -n market-entropy"
    echo "  kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring"
    echo ""
}

# Cleanup function for failed deployments
cleanup_on_failure() {
    warn "Deployment failed, cleaning up..."
    kubectl delete namespace market-entropy --ignore-not-found=true
    warn "Cleanup complete. Check logs above for errors."
}

# Main deployment function
main() {
    trap cleanup_on_failure ERR
    
    check_prerequisites
    generate_secrets
    build_and_push
    create_cluster
    install_addons
    setup_monitoring
    create_secrets
    deploy_application
    setup_ssl
    get_deployment_info
    
    success "🚀 MarketEntropy deployed successfully!"
}

# Handle command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "destroy")
        warn "Destroying MarketEntropy deployment..."
        kubectl delete namespace market-entropy --ignore-not-found=true
        eksctl delete cluster --name=${CLUSTER_NAME} --region=${REGION}
        success "Deployment destroyed"
        ;;
    "update")
        log "Updating MarketEntropy application..."
        build_and_push
        deploy_application
        success "Application updated"
        ;;
    "status")
        kubectl get all -n market-entropy
        ;;
    *)
        echo "Usage: $0 {deploy|destroy|update|status}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Full deployment (default)"
        echo "  destroy - Delete everything"
        echo "  update  - Update application only"
        echo "  status  - Show deployment status"
        exit 1
        ;;
esac
