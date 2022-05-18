from __future__ import annotations
import asyncio
import forta_agent
from forta_agent import get_json_rpc_url
from web3 import Web3
from src.db.db_utils import db_utils
from src.db.controller import init_async_db
from src.findings import UncertainPriorityFeeFindings, PriorityFeeFindings
from src.utils import get_protocols_by_chain, get_key_by_value, calculate_new_base_fee
from src.forecaster import forecast
from src.config import test_mode, history_capacity, minimal_capacity_to_forecast, critical_enable, high_enable, \
    medium_enable, low_enable, debug_logs_enabled, win_streak_limit

global blocks_counter
global current_capacity
global current_block

initialized = False
real_base_fee_detected = False
maybe_base_fee = float('inf')
win_streak = 0

web3 = Web3(Web3.HTTPProvider(get_json_rpc_url()))
chain_id = web3.eth.chain_id
protocols = get_protocols_by_chain(chain_id)
protocols_addresses = list(map(lambda x: Web3.toChecksumAddress(x).lower(), protocols.values()))


async def my_initialize(block_event: forta_agent.block_event.BlockEvent):
    """
    This function is initialize pattern, that is used instead the default Forta's initialize() because the block number
    is needed for the initialization
    @param block_event: block event received from the handle_block
    """
    global initialized
    global blocks_counter
    global current_capacity
    global current_block

    # initialize database tables
    transaction_table, blocks_table, future_table = await init_async_db(test_mode)
    db_utils.set_tables(transaction_table, blocks_table, future_table)

    # if the database is not empty (in case the agent was restarted) we need to clear the old blocks firstly
    await clean_db(block_event.block_number, blocks_table, transaction_table)

    current_block = block_event.block_number
    # we will count the blocks since agent's start
    blocks_counter = 0
    # also we need to know how many blocks left inside the db after the clean to decide is it possible to fit the model
    current_capacity = await blocks_table.count_rows()

    initialized = True


async def analyze_transaction(transaction_event: forta_agent.transaction_event.TransactionEvent):
    """
    This function is triggered by handle_transaction using function main(). It is responsible for the adding the
    transaction to the database and its analysis after. Also, this function will trigger the forecaster in case there is
    no forecasted values and the forecast is possible
    @param transaction_event: Transaction event received from handle_transaction()
    @return: Findings
    """
    global maybe_base_fee
    global real_base_fee_detected
    global current_block
    findings = []

    # Since we can't get the real base fee of the block from the block event, we will try to calculate it using the
    # cheapest transaction in the block. This process is better described in the readme.
    # Upd.: we will do it until completed win streak
    if not real_base_fee_detected and transaction_event.gas_price < maybe_base_fee and transaction_event.block_number == current_block:
        maybe_base_fee = transaction_event.gas_price

    # Then we will save and analyze the transactions only for our protocols
    if transaction_event.to in protocols_addresses:

        # get the database tables
        transactions = db_utils.get_transactions()
        blocks = db_utils.get_blocks()
        future = db_utils.get_future()

        # get the previous block
        prev_block_row = await blocks.get_row_by_criteria({'block': transaction_event.block.number - 1})
        prev_base_fee = prev_block_row.base_fee if prev_block_row else None

        # since we have forecasted value for each hour, we need to calculate the timestamp rounded for the hour
        hourly_timestamp = transaction_event.block.timestamp - transaction_event.block.timestamp % 3600
        # get these rows from the database
        future_rows = await future.get_all_rows_by_criteria({'timestamp': hourly_timestamp})
        # and extract the estimation for the current protocol
        future_row = None
        if future_rows:
            for fr in future_rows:
                if fr.contract == transaction_event.to:
                    future_row = fr
                    break

        # if there is no estimation in the database but the capacity is big enough to calculate it then we need to
        # trigger the forecaster
        if not future_row and current_capacity > minimal_capacity_to_forecast:
            await forecast(transaction_event.to)

            # and try to get the forecasted values again
            future_rows = await future.get_all_rows_by_criteria({'timestamp': hourly_timestamp})
            future_row = None
            if future_rows:
                for fr in future_rows:
                    if fr.contract == transaction_event.to:
                        future_row = fr
                        break

        # we need to determine how volatile the protocol is
        uncertainty = (future_row.priority_fee_upper - future_row.priority_fee_lower) if future_row else None
        priority_fee = None

        # Upd: after completing win streak we will calculate base_fee and priority_fee on the fly.
        # Knowing the real base fee for sure we don't need the estimation, so we will use separate alert class
        if real_base_fee_detected and prev_base_fee and future_row:
            base_fee = calculate_new_base_fee(prev_base_fee, prev_block_row.gas_limit_total,
                                              prev_block_row.gas_used_total)
            priority_fee = transaction_event.gas_price - base_fee
            error = priority_fee - future_row.priority_fee

            if debug_logs_enabled:
                print(f'INFO: Protocol: {get_key_by_value(protocols, transaction_event.to)}\n'
                      f'INFO: Real priority fee: {int(priority_fee / 10 ** 9)} GWei\n'
                      f'INFO: Excepted priority fee upper: {int(future_row.priority_fee_upper / 10 ** 9)} GWei\n'
                      f'INFO: Excepted priority fee lower: {int(future_row.priority_fee_lower / 10 ** 9)} GWei\n'
                      f'INFO: Excepted priority fee: {int(future_row.priority_fee / 10 ** 9)} GWei')

            if error > 2 * uncertainty and critical_enable:
                findings.append(PriorityFeeFindings.critical(protocols, transaction_event.to,
                                                             future_row.priority_fee_upper,
                                                             priority_fee, transaction_event.hash))
            elif error > 1.5 * uncertainty and high_enable:
                findings.append(PriorityFeeFindings.high(protocols, transaction_event.to, future_row.priority_fee_upper,
                                                         priority_fee, transaction_event.hash))
            elif error > uncertainty and medium_enable:
                findings.append(PriorityFeeFindings.medium(protocols, transaction_event.to,
                                                           future_row.priority_fee_upper,
                                                           priority_fee, transaction_event.hash))
            elif priority_fee > future_row.priority_fee_upper and low_enable:
                findings.append(PriorityFeeFindings.low(protocols, transaction_event.to, future_row.priority_fee_upper,
                                                        priority_fee, transaction_event.hash))

        elif prev_base_fee and future_row:

            base_fee_upper = prev_base_fee * 1.125  # according to the Ethereum YellowPaper the new base fee can not be
            base_fee_lower = prev_base_fee * 0.875  # greater or smaller than 12.5% relating to the previous base fee

            # but if there is already known transaction in this block with a smaller gas price then the upper base fee
            # is reduced to this value
            if maybe_base_fee < base_fee_upper:
                base_fee_upper = maybe_base_fee

            if base_fee_upper < base_fee_lower:
                base_fee_lower = base_fee_upper

            # now we can calculate an estimated range for the priority fee
            priority_fee_lower = transaction_event.gas_price - base_fee_upper
            priority_fee_upper = transaction_event.gas_price - base_fee_lower

            # we need to calculate the error range
            error_lower = priority_fee_lower - future_row.priority_fee
            error_upper = priority_fee_upper - future_row.priority_fee

            if debug_logs_enabled:
                print(f'INFO: Protocol: {get_key_by_value(protocols, transaction_event.to)}\n'
                      f'INFO: Upper priority fee: {int(priority_fee_upper / 10 ** 9)} GWei\n'
                      f'INFO: Lower priority fee: {int(priority_fee_lower / 10 ** 9)} GWei\n'
                      f'INFO: Excepted priority fee upper: {int(future_row.priority_fee_upper / 10 ** 9)} GWei\n'
                      f'INFO: Excepted priority fee lower: {int(future_row.priority_fee_lower / 10 ** 9)} GWei\n'
                      f'INFO: Excepted priority fee: {int(future_row.priority_fee / 10 ** 9)} GWei')

            # finally we can create the alert depending on how far the priority fee is from the estimated value
            if error_lower > 2 * uncertainty and critical_enable:
                findings.append(
                    UncertainPriorityFeeFindings.critical(protocols, transaction_event.to,
                                                          future_row.priority_fee_upper,
                                                          priority_fee_lower, transaction_event.hash))
            elif error_upper > 2 * uncertainty and high_enable:
                findings.append(
                    UncertainPriorityFeeFindings.high(protocols, transaction_event.to, future_row.priority_fee_upper,
                                                      priority_fee_lower, transaction_event.hash))
            elif priority_fee_lower > future_row.priority_fee_upper and medium_enable:
                findings.append(
                    UncertainPriorityFeeFindings.medium(protocols, transaction_event.to, future_row.priority_fee_upper,
                                                        priority_fee_lower, transaction_event.hash))
            elif priority_fee_upper > future_row.priority_fee_upper and low_enable:
                findings.append(
                    UncertainPriorityFeeFindings.low(protocols, transaction_event.to, future_row.priority_fee_upper,
                                                     priority_fee_lower, transaction_event.hash))

        elif real_base_fee_detected and prev_base_fee:
            base_fee = calculate_new_base_fee(prev_base_fee, prev_block_row.gas_limit_total,
                                              prev_block_row.gas_used_total)
            priority_fee = transaction_event.gas_price - base_fee

        # insert the transaction into the database
        await transactions.paste_row({'timestamp': transaction_event.block.timestamp, 'tx': transaction_event.hash,
                                      'block': transaction_event.block_number, 'contract': transaction_event.to,
                                      'gas': transaction_event.transaction.gas,
                                      'gas_price': transaction_event.transaction.gas_price,
                                      'priority_fee': priority_fee})

        if not prev_block_row:
            return []

    return findings


async def base_fee_logic(block_number: int):
    """
    This function is triggered by handle_block using function main(). It receives the previous block number,
    calculates its base fee and then calculates the priority fee for each transaction in this block.
    Upd.: This function works until real base fee will not be found. Until this moment the function also tries to
    find real base fee by calculating new base according to the Ethereum papers. If the minimal gas price of the
    transaction actually was block's base fee then it will complete win streak and the agent will be switched to the
    'real_base_fee_detected' mode. But if we will find the transaction that contains gas price lower than our calculated
    base fee then we will reset the win streak.
    @param block_number: Previous block number
    @return:
    """
    global maybe_base_fee
    global win_streak
    global real_base_fee_detected

    # get the necessary tables from the database
    blocks = db_utils.get_blocks()
    transactions = db_utils.get_transactions()

    # get the record 2 blocks behind the actual (remember that block_number in this function is actual_block_number - 1)
    prev_block = await blocks.get_row_by_criteria({'block': block_number - 1})
    calculated_base_fee = None

    if prev_block and prev_block.base_fee:

        # here we need to calculate the base fee as it is done in Ethereum
        calculated_base_fee = calculate_new_base_fee(prev_block.base_fee, prev_block.gas_limit_total,
                                                     prev_block.gas_used_total)

        # if the cheapest transaction == our calculated base fee then we increment win streak
        if calculated_base_fee == maybe_base_fee:
            win_streak += 1
        # but if it is smaller - then we reset the win streak
        elif maybe_base_fee < calculated_base_fee:
            win_streak = 0

        if debug_logs_enabled:
            print(f'INFO: Block: {block_number}')
            print(f'INFO: Calculated base fee: {calculated_base_fee}\n'
                  f'INFO: Maybe base fee: {maybe_base_fee}\n'
                  f'INFO: Current Win Streak: {win_streak}')

        # when the win streak is completed the agent will switch to the 'real_base_fee_detected' mode
        if win_streak == win_streak_limit:
            real_base_fee_detected = True
            if debug_logs_enabled:
                print("INFO: Win Streak limit was earned! The real base_fee was detected.")

                block = await blocks.get_row_by_criteria({'block': block_number})

                await blocks.update_row_by_criteria(
                    {'base_fee': calculate_new_base_fee(block.base_fee, block.gas_limit_total,
                                                        block.gas_used_total)}, {'block': block_number + 1})

        # if the previous block was empty we calculate its base fee
        if maybe_base_fee == float('inf'):
            maybe_base_fee = calculate_new_base_fee(prev_block.base_fee, prev_block.gas_limit_total,
                                                    prev_block.gas_used_total)

    # if we have any win streak we fill the database with calculated values, but if our streak was reset then we
    # suppose to insert the cheapest transaction's gas_price
    base_fee_to_insert = calculated_base_fee if win_streak != 0 and calculated_base_fee else maybe_base_fee
    await blocks.update_row_by_criteria(
        {'base_fee': base_fee_to_insert}, {'block': block_number})

    # and reset the maybe_base_fee for the next block
    maybe_base_fee = float('inf')

    # then we will need to update all the transactions for the previous block with calculated priority fees
    transactions_in_block = await transactions.get_all_rows_by_criteria({'block': block_number})
    transactions_hashes_and_priority_fees = {tx.tx: tx.gas_price - base_fee_to_insert for tx in transactions_in_block}
    for tx, priority_fee in transactions_hashes_and_priority_fees.items():
        await transactions.update_row_by_criteria({'priority_fee': priority_fee}, {'tx': tx})


async def analyze_blocks(block_event: forta_agent.block_event.BlockEvent) -> None:
    """
    This function is triggered by handle_block using function main(). It is responsible for the adding blocks to the
    database and clean the database every 1k blocks.
    @param block_event: Block event received from handle_block()
    @return:
    """
    global maybe_base_fee
    global blocks_counter
    global current_capacity
    global real_base_fee_detected
    global current_block
    global win_streak

    blocks = db_utils.get_blocks()
    transactions = db_utils.get_transactions()

    prev_block = await blocks.get_row_by_criteria({'block': block_event.block_number - 1})

    # if the node somehow lose any block than we need to reset win streak and switch back to the undetected mode
    if current_block + 1 != block_event.block_number or block_event.block.parent_hash != prev_block.block_hash:
        if debug_logs_enabled:
            print("INFO: Fork block was received or block was missed, recalculating base fee...")
        real_base_fee_detected = False
        win_streak = 0
    current_block = block_event.block_number

    # in case we already found the real base fee we can insert it on the fly, else we will do it with the next block
    # in the base_fee_logic() function.
    if real_base_fee_detected:
        if not prev_block.base_fee:
            prev_prev_row = await blocks.get_row_by_criteria({'block': block_event.block_number - 2})
            prev_base_fee = calculate_new_base_fee(prev_prev_row.base_fee, prev_prev_row.gas_limit_total,
                                                   prev_prev_row.gas_used_total)
            blocks.update_row_by_criteria({'base_fee': prev_base_fee}, {'block': block_event.block_number - 1})
            prev_block.base_fee = prev_base_fee
        base_fee = calculate_new_base_fee(prev_block.base_fee, prev_block.gas_limit_total,
                                          prev_block.gas_used_total)
    else:
        base_fee = None

    # clean the database every 1k blocks
    blocks_counter += 1
    if blocks_counter > 1000:
        await clean_db(block_event.block_number, blocks, transactions)
        current_capacity = await blocks.count_rows()
        blocks_counter = 0

    # add the block to the database
    await blocks.paste_row({'block': block_event.block_number, 'block_hash': block_event.block_hash,
                            'gas_used_total': int(block_event.block.gas_used, 0),
                            'gas_limit_total': int(block_event.block.gas_limit, 0),
                            'base_fee': base_fee})


async def clean_db(block_number: int, blocks, transactions):
    """
    this function removes old rows from the database
    @param block_number:
    @param blocks:
    @param transactions:
    @return:
    """

    await asyncio.gather(
        blocks.delete_old(block_number, history_capacity),
        transactions.delete_old(block_number, history_capacity),
    )


async def main(event: forta_agent.transaction_event.TransactionEvent | forta_agent.block_event.BlockEvent):
    """
    This function is used to start logic functions in the different threads and then gather the findings
    """
    global initialized
    global blocks_counter
    global real_base_fee_detected

    if isinstance(event, forta_agent.transaction_event.TransactionEvent):
        return await asyncio.gather(
            analyze_transaction(event),
        )
    else:
        if not initialized:
            await my_initialize(event)
        await asyncio.gather(
            analyze_blocks(event),
            base_fee_logic(event.block_number - 1),
        ) if not real_base_fee_detected else await analyze_blocks(event)
        return []


def provide_handle_transaction():
    """
    This function is just a wrapper for the handle_transaction()
    @return:
    """

    def wrapped_handle_transaction(transaction_event: forta_agent.transaction_event.TransactionEvent) -> list:
        return [finding for findings in asyncio.run(main(transaction_event)) for finding in findings]

    return wrapped_handle_transaction


def provide_handle_block():
    """
    This function is just a wrapper for the handle_block()
    @return:
    """

    def wrapped_handle_block(block_event: forta_agent.block_event.BlockEvent) -> list:
        return [finding for findings in asyncio.run(main(block_event)) for finding in findings]

    return wrapped_handle_block


def handle_transaction(transaction_event: forta_agent.transaction_event.TransactionEvent):
    """
    This function is used by Forta SDK
    @param transaction_event: forta_agent.transaction_event.TransactionEvent
    @return:
    """
    return provide_handle_transaction()(transaction_event)


def handle_block(block_event: forta_agent.block_event.BlockEvent):
    """
    This function is used by Forta SDK
    @param block_event: forta_agent.block_event.BlockEvent
    @return:
    """
    return provide_handle_block()(block_event)
