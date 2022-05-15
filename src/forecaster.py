import logging
import pandas as pd
from prophet import Prophet
import warnings
from src.db.db_utils import db_utils

logger = logging.getLogger('prophet')
logger.setLevel(logging.ERROR)
logger = logging.getLogger('cmdstanpy')
logger.setLevel(logging.ERROR)
logger = logging.getLogger('stanpy')
logger.setLevel(logging.ERROR)
warnings.simplefilter(action='ignore')


async def forecast(protocol: str):
    transaction_table = db_utils.get_transactions()
    future_table = db_utils.get_future()
    transactions_rows = await transaction_table.get_all_rows_by_criteria({'contract': protocol})

    if len(transactions_rows) < 2:
        return

    df = pd.DataFrame([t.__dict__ for t in transactions_rows])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    df = df.set_index('timestamp').resample('H').max().reset_index()

    train = df.reset_index()[['timestamp', 'priority_fee']].rename({'timestamp': 'ds', 'priority_fee': 'y'},
                                                                   axis='columns')

    m = Prophet()
    m.fit(train)
    future = m.make_future_dataframe(periods=24, freq='H')

    forecast_rows = m.predict(future)

    await future_table.delete_row_by_contract(protocol)
    for index, row in forecast_rows.iterrows():
        await future_table.paste_row(
            {'contract': protocol, 'timestamp': int(row['ds'].timestamp()), 'priority_fee': int(row['yhat']),
             'priority_fee_lower': int(row['yhat_lower']), 'priority_fee_upper': int(row['yhat_upper'])})
