import random

from forta_agent import FindingSeverity, create_transaction_event, create_block_event
from web3 import Web3

from src.agent import provide_handle_transaction, provide_handle_block
from src.utils import calculate_new_base_fee, get_protocols_by_chain

FREE_ETH_ADDRESS = "0xE0dD882D4dA747e9848D05584e6b42c6320868be"
protocols = get_protocols_by_chain(1)
protocols_addresses = list(map(lambda x: Web3.toChecksumAddress(x).lower(), protocols.values()))


class TestSmartGasUsageAgent:
    def test_block_fee_calculation(self):
        """
        this test is based on the real data retried from the etherscan:
        https://etherscan.io/block/14744240
        https://etherscan.io/block/14744241
        https://etherscan.io/block/14744242
        https://etherscan.io/block/14744243
        https://etherscan.io/block/14744244
        @return:
        """

        block_14744240_gas_used = 6223756
        block_14744240_gas_limit = 30000000
        block_14744240_base_fee = 135022850976

        block_14744241_gas_used = 10882484
        block_14744241_gas_limit = 30000000
        block_14744241_base_fee = 125147905262

        block_14744242_gas_used = 29988124
        block_14744242_gas_limit = 30000000
        block_14744242_base_fee = 120853751077

        block_14744243_gas_used = 27143187
        block_14744243_gas_limit = 30000000
        block_14744243_base_fee = 135948509468

        block_14744244_base_fee = 149705577575

        my_bf_41 = calculate_new_base_fee(block_14744240_base_fee, block_14744240_gas_limit, block_14744240_gas_used)
        my_bf_42 = calculate_new_base_fee(my_bf_41, block_14744241_gas_limit, block_14744241_gas_used)
        my_bf_43 = calculate_new_base_fee(my_bf_42, block_14744242_gas_limit, block_14744242_gas_used)
        my_bf_44 = calculate_new_base_fee(my_bf_43, block_14744243_gas_limit, block_14744243_gas_used)

        assert my_bf_41 == block_14744241_base_fee
        assert my_bf_42 == block_14744242_base_fee
        assert my_bf_43 == block_14744243_base_fee
        assert my_bf_44 == block_14744244_base_fee

    def test_returns_zero_finding_if_the_priority_fee_is_small(self):
        tx_event = create_transaction_event({
            'transaction': {
                'from': FREE_ETH_ADDRESS,
                'to': random.choice(protocols_addresses),
                'gas_price': 1000000000,

            },
            'block': {
                'number': 14442800,
                'timestamp': 1648041590,
            },
        })

        block_event = create_block_event({
            'block': {
                'number': 14442800,
                'timestamp': 1648041590,
                'gas_used': hex(18627147),
                'gas_limit': hex(30029295)
            }
        })

        provide_handle_block()(block_event)
        findings = provide_handle_transaction()(tx_event)
        assert len(findings) == 0

    def test_returns_critical_findings_if_the_priority_fee_is_very_big(self):
        tx_event = create_transaction_event({
            'transaction': {
                'from': FREE_ETH_ADDRESS,
                'to': protocols.get('OpenSea').lower(),
                'gas_price': 10000000000000,

            },
            'block': {
                'number': 14442800,
                'timestamp': 1648041590,
            },
        })

        findings = provide_handle_transaction()(tx_event)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.Critical

    def test_returns_critical_findings_for_ronin_bridge_if_priority_fee_is_100_gwei(self):
        base_fee = 15566665807
        priority_fee = 100000000000
        tx_event = create_transaction_event({
            'transaction': {
                'from': FREE_ETH_ADDRESS,
                'to': protocols.get('RoninBridge').lower(),
                'gas_price': base_fee + priority_fee,

            },
            'block': {
                'number': 14442800,
                'timestamp': 1648041590,
            },
        })

        findings = provide_handle_transaction()(tx_event)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.Critical

    def test_returns_returns_zero_findings_for_opensea_if_priority_fee_is_100_gwei(self):
        base_fee = 15566665807
        priority_fee = 100000000000
        tx_event = create_transaction_event({
            'transaction': {
                'from': FREE_ETH_ADDRESS,
                'to': protocols.get('OpenSea').lower(),
                'gas_price': base_fee + priority_fee,

            },
            'block': {
                'number': 14442800,
                'timestamp': 1648041590,
            },
        })

        findings = provide_handle_transaction()(tx_event)
        assert len(findings) == 0

    def test_for_the_same_gas_price_and_protocol_returns_zero_or_one_finding_depending_on_the_seasonality(self):
        gas_price = 2550000000000
        tx_event = create_transaction_event({
            'transaction': {
                'from': FREE_ETH_ADDRESS,
                'to': protocols.get('OpenSea').lower(),
                'gas_price': gas_price,

            },
            'block': {
                'number': 14442800,
                'timestamp': 1648041590,
            },
        })

        findings = provide_handle_transaction()(tx_event)
        assert len(findings) == 1

        tx_event = create_transaction_event({
            'transaction': {
                'from': FREE_ETH_ADDRESS,
                'to': protocols.get('OpenSea').lower(),
                'gas_price': gas_price,

            },
            'block': {
                'number': 14444500,
                'timestamp': 1648064536,
            },
        })

        findings = provide_handle_transaction()(tx_event)
        assert len(findings) == 0
