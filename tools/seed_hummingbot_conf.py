"""
Seed a Hummingbot conf/ directory with a single hyperliquid_perpetual_testnet
connector config (arb_wallet mode) + password verification file.

Designed to run inside the hummingbot conda env (sandbox/Dockerfile.hummingbot).
The output conf dir is then bind-mounted into the long-running testnet container.

Required env vars:
    CONFIG_PASSWORD                   password to encrypt secrets with
    HYPERLIQUID_TESTNET_PRIVATE_KEY   testnet Arbitrum wallet private key (hex, 0x...)

Optional:
    HL_TESTNET_ADDRESS   Arbitrum wallet address. If unset, derived from the key.
    OUT_DIR              target conf dir on container filesystem.
                         Defaults to /app/conf (Hummingbot's default CONF_DIR_PATH).
"""

import os
import sys
from pathlib import Path

os.chdir("/app")
sys.path.insert(0, "/app")

from eth_account import Account

from hummingbot.client.config.config_crypt import (
    ETHKeyFileSecretManger,
    PASSWORD_VERIFICATION_PATH,
    store_password_verification,
)
from hummingbot.client.config.config_helpers import (
    ClientConfigAdapter,
    get_connector_config_yml_path,
    save_to_yml,
)
from hummingbot.client.config.security import Security
from hummingbot.client.settings import CONF_DIR_PATH, CONNECTORS_CONF_DIR_PATH
from hummingbot.connector.derivative.hyperliquid_perpetual.hyperliquid_perpetual_utils import (
    HyperliquidPerpetualTestnetConfigMap,
)


def main() -> None:
    password = os.environ["CONFIG_PASSWORD"]
    private_key = os.environ["HYPERLIQUID_TESTNET_PRIVATE_KEY"]
    address = os.environ.get("HL_TESTNET_ADDRESS") or Account.from_key(private_key).address

    CONF_DIR_PATH.mkdir(parents=True, exist_ok=True)
    CONNECTORS_CONF_DIR_PATH.mkdir(parents=True, exist_ok=True)

    secrets_manager = ETHKeyFileSecretManger(password)
    if not PASSWORD_VERIFICATION_PATH.exists():
        store_password_verification(secrets_manager)
    Security.secrets_manager = secrets_manager

    cfg = HyperliquidPerpetualTestnetConfigMap(
        hyperliquid_perpetual_testnet_mode="api_wallet",
        use_vault=False,
        hyperliquid_perpetual_testnet_address=address,
        hyperliquid_perpetual_testnet_secret_key=private_key,
    )
    adapter = ClientConfigAdapter(cfg)
    yml_path = get_connector_config_yml_path("hyperliquid_perpetual_testnet")
    save_to_yml(yml_path, adapter)
    print(f"Seeded {yml_path} for address {address}")


if __name__ == "__main__":
    main()
