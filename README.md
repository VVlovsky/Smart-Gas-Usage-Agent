# **Smart Gas Usage Agent**

---

## Description

This bot determines an abnormally high priority fee for the specified protocols. 
This is done using an algorithm for determining the priority fee, as well as separate storage of this information 
in the database and subsequent analysis using machine learning.

It is worth noting that the bot considers the priority fee component, and not the gas price of the transaction itself. 
This was done due to the fact that it is impossible to foresee or calculate the load of the Ethereum network and an 
accidental event (for example, NFT minting) will provoke a sharp increase in the gas price, which will lead to spam 
alerts. As we remember, `gas_price = base_fee + priority_fee`, therefore, in order to exclude the network congestion 
component, we need to subtract the base fee from the gas price. The problem is that there is no direct way to get the 
base fee using the Forta SDK, and using third-party APIs is problematic. To solve this problem, the following algorithm 
was developed: the bot works in two phases 
- The `Phase 1` is when the base_fee is unknown to us. During this phase the 
bot collects the gas price for all block transactions and assumes that the minimum of them is the base fee of this 
block. Then the win streak count starts. Each next block the gas is considered according to how it is implemented in 
EIP-1559, and we are also looking for the transaction with the lowest gas price. If the calculated value is equal to 
the price of this transaction, we assume that the value was initially guessed correctly and increment win streak, and 
if the gas price of the cheapest transaction turns out to be lower than the calculated value, then this means that we 
made a mistake in the base value, hence we reset win streak and take a new base value for the calculation. When the win 
streak reaches the limit of a certain value specified in the parameters, we assert that the base fee is defined 
correctly and the bot enters the second phase. It is worth noting that in this phase the bot works and detects 
anomalies, however, it operates on the ranges of possible values, and the priority fee for transactions in the database 
is filled one block late. 
- The `Phase 2` is that we know the base fee for sure and stop using possible ranges, we begin to 
fill the database completely without delay in one block, part of the functionality of the first phase is disabled, 
which reduces the number of requests to the database, speeds up the agent and increases it accuracy, because now we 
can calculate the priority fee of the transaction for sure.

When the bot collects enough data, regardless of the phase, the forecast algorithm will be run on the available data. 
The TODS library with the DeepLog algorithm, which uses LSTM networks, and the Prophet library, 
which uses Fourier series, proved to be the best for this. It was decided that for the stability of the bot and 
greater versatility, it is better to use the Prophet library and consider TODS as an experimental backend with 
a possibility to use it in the future.

## Features
- Fully asynchronous local database
- Bot is stable after the sudden restart
- Alerts are independent of the base block fee
- Single line protocol change

## Chains

- Full support
  - Ethereum
- Partial support
  - Polygon - should work but requires more tests
  - Avalanche - should work but requires more tests
- Unsupported
  - Fantom - EIP-1559 not implemented
  - BSC - EIP-1559 not implemented
  - Optimism - L2
  - Arbitrum - L2

## Settings

You can specify your own settings in the `src/config.py`:

```python
test_mode = False  # The mode when the bot uses test database
debug_logs_enabled = False  # Print the debug logs
history_capacity = 6300 * 7  # The amount of blocks to store in the database
minimal_capacity_to_forecast = 6300 * 3  # The minimal amount of the blocks to start forecasting
critical_enable = True  # Enables critical alerts
high_enable = True  # Enables high alerts
medium_enable = True  # Enables medium alerts
low_enable = True  # Enables low alerts
win_streak_limit = 10  # The needed amount of successful checks to be sure that the base_fee was properly calculated

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
```

## Alerts

- SMART-PRIORITY-FEE-UNCERTAIN
  - Fired when an estimated transaction priority fee is higher then forecasted
  - Severity depends on how higher it is:
    - `Critical` - lower estimated fee - forecasted fee > 2 * (forecasted upper fee - forecasted lower fee)
    - `High` - upper estimated fee - forecasted fee > 2 * (forecasted upper fee - forecasted lower fee)
    - `Medium` - lower estimated fee  > forecasted upper fee
    - `Low` - upper estimated fee > forecasted upper fee
  - Type is always set to "Suspicious"
  - Metadata contains:
    - `protocol_address` - the address of the protocol
    - `excepted_max_fee` - the forecasted max fee (in GWei)
    - `estimated_min_priority_fee` - the estimated min priority fee of the transaction (in GWei)
    - `tx_hash` - the hash of the transaction
    
- SMART-PRIORITY-FEE
  - Fired when the real transaction priority fee is higher then forecasted
  - Severity depends on how higher it is:
    - `Critical` - real priority fee - forecasted fee > 2 * (forecasted upper fee - forecasted lower fee)
    - `High` - real priority fee - forecasted fee > 1.5 * (forecasted upper fee - forecasted lower fee)
    - `Medium` - real priority fee - forecasted fee > forecasted upper fee - forecasted lower fee
    - `Low` - real priority fee > forecasted upper fee
  - Type is always set to "Suspicious"
  - Metadata contains:
    - `protocol_address` - the address of the protocol
    - `excepted_max_fee` - the forecasted max fee (in GWei)
    - `real_priority_fee` - the estimated min priority fee of the transaction (in GWei)
    - `tx_hash` - the hash of the transaction

## Tests

Tests and test data use database preset `test/database_presets/test_14442765-14489802.db` that contains real collected 
data. It should be moved to `./test.db` e.g.
```bash
cp ./test/database_presets/test_14442765-14489802.db ./test.db
```

There are 7 tests that should pass:

```python
test_block_fee_calculation()
test_returns_zero_finding_if_the_priority_fee_is_small()
test_returns_critical_findings_if_the_priority_fee_is_very_big()
test_returns_critical_findings_for_ronin_bridge_if_priority_fee_is_100_gwei()
test_returns_returns_zero_findings_for_opensea_if_priority_fee_is_100_gwei()
test_for_the_same_gas_price_and_protocol_returns_zero_or_one_finding_depending_on_the_seasonality()
```

## Test Data

The agent easy detects RoninBridge hack. In 1st Phase the bot will return next findings for this hack:
```json
-> npm run range 14442835..14442841
...
1 findings for transaction 0xc28fad5e8d5e0ce6a2eaf67b6687be5d58113e16be590824d6cfa1a94467d0b7 {
  "name": "Critical Priority Fee for RoninBridge",
  "description": "Priority fee for RoninBridge is critically higher than excepted!",
  "alertId": "SMART-PRIORITY-FEE-UNCERTAIN",
  "protocol": "ethereum",
  "severity": "Critical",
  "type": "Suspicious",
  "metadata": {
    "protocol_address": "0x1a2a1c938ce3ec39b6d47113c7955baa9dd454f2",
    "excepted_max_fee": 18.216737495,
    "estimated_min_priority_fee": 66.848563939,
    "tx_hash": "0xc28fad5e8d5e0ce6a2eaf67b6687be5d58113e16be590824d6cfa1a94467d0b7"
  },
  "addresses": []
}
...
1 findings for transaction 0xed2c72ef1a552ddaec6dd1f5cddf0b59a8f37f82bdda5257d9c7c37db7bb9b08 {
  "name": "Critical Priority Fee for RoninBridge",
  "description": "Priority fee for RoninBridge is critically higher than excepted!",
  "alertId": "SMART-PRIORITY-FEE-UNCERTAIN",
  "protocol": "ethereum",
  "severity": "Critical",
  "type": "Suspicious",
  "metadata": {
    "protocol_address": "0x1a2a1c938ce3ec39b6d47113c7955baa9dd454f2",
    "excepted_max_fee": 18.216737495,
    "estimated_min_priority_fee": 63.866976836,
    "tx_hash": "0xed2c72ef1a552ddaec6dd1f5cddf0b59a8f37f82bdda5257d9c7c37db7bb9b08"
  },
  "addresses": []
}
```

In 2nd Phase the bot will return next findings for this hack:

```json
-> npm run range 14442810..14442841
...
1 findings for transaction 0xc28fad5e8d5e0ce6a2eaf67b6687be5d58113e16be590824d6cfa1a94467d0b7 {
  "name": "Critical Priority Fee for RoninBridge",
  "description": "Priority fee for RoninBridge is critically higher than excepted!",
  "alertId": "SMART-PRIORITY-FEE",
  "protocol": "ethereum",
  "severity": "Critical",
  "type": "Suspicious",
  "metadata": {
    "protocol_address": "0x1a2a1c938ce3ec39b6d47113c7955baa9dd454f2",
    "excepted_max_fee": 18.216737495,
    "real_priority_fee": 66.848563939,
    "tx_hash": "0xc28fad5e8d5e0ce6a2eaf67b6687be5d58113e16be590824d6cfa1a94467d0b7"
  },
  "addresses": []
}
...
1 findings for transaction 0xed2c72ef1a552ddaec6dd1f5cddf0b59a8f37f82bdda5257d9c7c37db7bb9b08 {
  "name": "Critical Priority Fee for RoninBridge",
  "description": "Priority fee for RoninBridge is critically higher than excepted!",
  "alertId": "SMART-PRIORITY-FEE",
  "protocol": "ethereum",
  "severity": "Critical",
  "type": "Suspicious",
  "metadata": {
    "protocol_address": "0x1a2a1c938ce3ec39b6d47113c7955baa9dd454f2",
    "excepted_max_fee": 18.216737495,
    "real_priority_fee": 64.866976836,
    "tx_hash": "0xed2c72ef1a552ddaec6dd1f5cddf0b59a8f37f82bdda5257d9c7c37db7bb9b08"
  },
  "addresses": []
}
```

Also the bot detects many other strange transactions like this one in OpenSea:
```json
1 findings for transaction 0x6d4190b3b9f796de3bef62c366f73c240499ff7e2d7dc5cabb0696704aeb4e2b {
  "name": "Critical Priority Fee for OpenSea",
  "description": "Priority fee for OpenSea is critically higher than excepted!",
  "alertId": "SMART-PRIORITY-FEE-UNCERTAIN",
  "protocol": "ethereum",
  "severity": "Critical",
  "type": "Suspicious",
  "metadata": {
    "protocol_address": "0x7f268357a8c2552623316e2562d90e642bb538e5",
    "excepted_max_fee": 3064.16855925,
    "estimated_min_priority_fee": 8840.72239151,
    "tx_hash": "0x6d4190b3b9f796de3bef62c366f73c240499ff7e2d7dc5cabb0696704aeb4e2b"
  },
  "addresses": []
}
```

or the same transaction but in the 2nd Phase:

```json
1 findings for transaction 0x6d4190b3b9f796de3bef62c366f73c240499ff7e2d7dc5cabb0696704aeb4e2b {
  "name": "Critical Priority Fee for OpenSea",
  "description": "Priority fee for OpenSea is critically higher than excepted!",
  "alertId": "SMART-PRIORITY-FEE",
  "protocol": "ethereum",
  "severity": "Critical",
  "type": "Suspicious",
  "metadata": {
    "protocol_address": "0x7f268357a8c2552623316e2562d90e642bb538e5",
    "excepted_max_fee": 3064.16855925,
    "real_priority_fee": 8841.72239151,
    "tx_hash": "0x6d4190b3b9f796de3bef62c366f73c240499ff7e2d7dc5cabb0696704aeb4e2b"
  },
  "addresses": []
}

```
