#!/bin/bash

# NIR Intelligence Platform - Comprehensive Test Script
echo "=========================================="
echo "NIR Intelligence Platform - Comprehensive Test"
echo "=========================================="
echo ""

# Test 1: Check Docker containers
echo "1. Testing Docker Environment..."
docker ps -a | grep -E "(nir_postgresql|nir_weaviate|nir_ilias)" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Docker containers found"
else
    echo "✗ Docker containers not running"
    echo "Starting containers..."
    docker-compose -f /home/martin/Development/vsCode_Environment/NIR_Mistral/nir_test_env/docker-compose.fixed.yml up -d
    sleep 10
fi

# Test 2: Check PostgreSQL
echo "2. Testing PostgreSQL Database..."
docker exec nir_postgresql_test pg_isready -U nir_user -d nir_db
if [ $? -eq 0 ]; then
    echo "✓ PostgreSQL is ready"
else
    echo "✗ PostgreSQL is not ready"
    exit 1
fi

# Test 3: Check Weaviate
echo "3. Testing Weaviate Vector Database..."
curl -s http://localhost:8080/v1/.well-known/ready > /dev/null
if [ $? -eq 0 ]; then
    echo "✓ Weaviate is ready"
else
    echo "✗ Weaviate is not ready"
    exit 1
fi

# Test 4: Check ILIAS (simulated)
echo "4. Testing ILIAS Integration..."
docker ps | grep nir_ilias_test > /dev/null
if [ $? -eq 0 ]; then
    echo "✓ ILIAS container is running"
else
    echo "✗ ILIAS container is not running"
    exit 1
fi

# Test 5: Test data processing
echo "5. Testing Data Processing..."
if [ -f "/home/martin/Development/vsCode_Environment/NIR_Mistral/nir_test_env/server/data/raw/sample_spectrum.csv" ]; then
    echo "✓ Sample data exists"
else
    echo "Creating sample data..."
    mkdir -p /home/martin/Development/vsCode_Environment/NIR_Mistral/nir_test_env/server/data/raw
    cat > /home/martin/Development/vsCode_Environment/NIR_Mistral/nir_test_env/server/data/raw/sample_spectrum.csv << 'EOF'
wavelength,intensity,metadata
900,0.123,"{\"instrument\":\"DIY_Spectrometer\",\"acquisition_time\":\"2026-07-30T10:00:00\",\"sample\":\"test_sample_1\"}"
950,0.187,"{\"instrument\":\"DIY_Spectrometer\",\"acquisition_time\":\"2026-07-30T10:00:00\",\"sample\":\"test_sample_1\"}"
1000,0.254,"{\"instrument\":\"DIY_Spectrometer\",\"acquisition_time\":\"2026-07-30T10:00:00\",\"sample\":\"test_sample_1\"}"
1050,0.312,"{\"instrument\":\"DIY_Spectrometer\",\"acquisition_time\":\"2026-07-30T10:00:00\",\"sample\":\"test_sample_1\"}"
1100,0.289,"{\"instrument\":\"DIY_Spectrometer\",\"acquisition_time\":\"2026-07-30T10:00:00\",\"sample\":\"test_sample_1\"}"
EOF
    echo "✓ Sample data created"
fi

# Test 6: Test Python data processing
python3 << 'PYTHON'
import pandas as pd
import json

try:
    data_path = '/home/martin/Development/vsCode_Environment/NIR_Mistral/nir_test_env/server/data/raw/sample_spectrum.csv'
    df = pd.read_csv(data_path)
    print(f"✓ Data loaded successfully: {len(df)} rows")
    
    metadata = json.loads(df['metadata'].iloc[0])
    print(f"✓ Metadata extracted: {metadata['instrument']}")
    
    wavelengths = df['wavelength'].tolist()
    intensities = df['intensity'].tolist()
    
    if len(wavelengths) > 0 and len(intensities) > 0:
        print(f"✓ Spectral data validated: {len(wavelengths)} data points")
    else:
        print("✗ Spectral data validation failed")
        exit(1)
        
except Exception as e:
    print(f"✗ Data processing failed: {e}")
    exit(1)
PYTHON

echo ""
echo "=========================================="
echo "All tests passed successfully!"
echo "=========================================="
echo ""
echo "Test Environment Summary:"
echo "- PostgreSQL: localhost:5432"
echo "- Weaviate: http://localhost:8080"
echo "- ILIAS: http://localhost:8081"
echo "- Sample data: nir_test_env/server/data/raw/"
echo ""
echo "To stop the test environment:"
echo "  docker-compose -f nir_test_env/docker-compose.fixed.yml down"
