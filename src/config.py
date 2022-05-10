test_mode = False  # The mode when the bot uses test database
debug_logs_enabled = False  # Print the debug logs
history_capacity = 6300 * 7  # The amount of blocks to store in the database
minimal_capacity_to_forecast = 6300 * 3  # The minimal amount of the blocks to start forecasting
critical_enable = True  # Enables critical alerts
high_enable = True  # Enables high alerts
medium_enable = True  # Enables medium alerts
low_enable = True  # Enables low alerts
win_streak_limit = 20  # The needed amount of successful checks to be sure that the base_fee was properly calculated

# Specify your own protocols for the Ethereum here
ETHER_protocols = {
    "OpenSea": "0x7f268357A8c2552623316e2562D90e642bB538E5",
    "RoninBridge": "0x1a2a1c938ce3ec39b6d47113c7955baa9dd454f2",
    "Uniswap": "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
    "1Inch": "0x1111111254fb6c44bAC0beD2854e76F90643097d",
    "FTX_EX": "0xC098B2a3Aa256D2140208C3de6543aAEf5cd3A94",
    "Metamask_DEX": "0x881D40237659C251811CEC9c364ef91dC08D300C",
    "GravityBridge": "0xa4108aA1Ec4967F8b52220a4f7e94A8201F2D906"
}

# Specify your own protocols for the Polygon here
POLYGON_protocols = {
    "Uniswap": "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45"
}

# Specify your own protocols for the Avalanche here
AVALANCHE_protocols = {
    "JoeRouter": "0x60aE616a2155Ee3d9A68541Ba4544862310933d4"
}

# ---------------- Next networks are disabled ---------------- #
FANTOM_protocols = {
    "SpookySwap": "0xF491e7B69E4244ad4002BC14e878a34207E38c29"
}

BSC_protocols = {
    "PancakeSwap": "0x10ED43C718714eb63d5aA57B78B54704E256024E"
}

OPTIMISM_protocols = {

}

ARBITRUM_protocols = {

}
