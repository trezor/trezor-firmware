#!/bin/sh

if [ ! -d "tropic-model" ]; then
    echo "================================================="
    echo "Please install the Tropic model to the tropic-model/ directory first, using the steps below!"
    echo "1. mkdir tropic-model && python3 -mvenv tropic-model/venv && source tropic-model/venv/bin/activate"
    echo "2. Follow instructions here: https://github.com/tropicsquare/ts-tvl/tree/master?tab=readme-ov-file#installing"
    echo "   (basically, download the tvl-XXX.whl and pip install it under the venv created above - which should be already activated)"
    echo "3. Get config files for the model from https://github.com/tropicsquare/ts-tvl/tree/master/tvl/server/model_config"
    echo "  i. model_config.yml"
    echo "  ii. tropic01_ese_certificate_1.pem"
    echo "  iii.tropic01_ese_private_key_1.pem"
    echo "  iv. tropic01_ese_public_key_1.pem"
    echo "================================================="
    exit 1
fi

cd tropic-model
source venv/bin/activate
model_server tcp -vv -c model_config.yml
