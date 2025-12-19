#!/bin/bash
# Script to view telemetry metrics for main_service

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-fabled-rookery-476623-g5}"
SERVICE_NAME="main-service"
REGION="${REGION:-us-central1}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  main_service Telemetry Viewer${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "Please authenticate with gcloud first:"
    echo "  gcloud auth login"
    exit 1
fi

echo -e "${GREEN}Project:${NC} $PROJECT_ID"
echo -e "${GREEN}Service:${NC} $SERVICE_NAME"
echo ""

# Function to query metrics
query_metric() {
    local metric_type=$1
    local description=$2
    
    echo -e "${BLUE}--- $description ---${NC}"
    echo "Metric: $metric_type"
    echo ""
    
    gcloud monitoring time-series list \
        --filter="metric.type=\"$metric_type\"" \
        --project="$PROJECT_ID" \
        --format="table(metric.labels, points[0].value.doubleValue, points[0].interval.endTime)" \
        --limit=10 2>/dev/null || {
        echo -e "${YELLOW}No data available yet (metrics may take 1-2 minutes to appear)${NC}"
    }
    echo ""
}

# Available metrics
echo -e "${GREEN}Available Custom Metrics:${NC}"
echo ""
echo "1. Message Processing Duration"
echo "2. Message Processing Total (Success/Failure)"
echo "3. Message Processing Errors (by type)"
echo "4. Poll Cycle Duration"
echo "5. Poll Cycles Total"
echo "6. View all metrics"
echo "7. Open Cloud Console"
echo "8. Exit"
echo ""

while true; do
    read -p "Select an option (1-8): " choice
    
    case $choice in
        1)
            query_metric "custom.googleapis.com/main_service/message_processing_duration" \
                "Message Processing Duration"
            ;;
        2)
            query_metric "custom.googleapis.com/main_service/message_processing_total" \
                "Message Processing Total (Success/Failure)"
            ;;
        3)
            query_metric "custom.googleapis.com/main_service/message_processing_errors_total" \
                "Message Processing Errors (by type)"
            ;;
        4)
            query_metric "custom.googleapis.com/main_service/poll_cycle_duration" \
                "Poll Cycle Duration"
            ;;
        5)
            query_metric "custom.googleapis.com/main_service/poll_cycles_total" \
                "Poll Cycles Total"
            ;;
        6)
            echo -e "${BLUE}--- All Custom Metrics ---${NC}"
            echo ""
            query_metric "custom.googleapis.com/main_service/message_processing_duration" \
                "Message Processing Duration"
            query_metric "custom.googleapis.com/main_service/message_processing_total" \
                "Message Processing Total"
            query_metric "custom.googleapis.com/main_service/message_processing_errors_total" \
                "Message Processing Errors"
            query_metric "custom.googleapis.com/main_service/poll_cycle_duration" \
                "Poll Cycle Duration"
            query_metric "custom.googleapis.com/main_service/poll_cycles_total" \
                "Poll Cycles Total"
            ;;
        7)
            echo "Opening Cloud Console Monitoring..."
            open "https://console.cloud.google.com/monitoring/metrics-explorer?project=$PROJECT_ID" 2>/dev/null || \
            xdg-open "https://console.cloud.google.com/monitoring/metrics-explorer?project=$PROJECT_ID" 2>/dev/null || \
            echo "Please open: https://console.cloud.google.com/monitoring/metrics-explorer?project=$PROJECT_ID"
            ;;
        8)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "Invalid option. Please select 1-8."
            ;;
    esac
done
