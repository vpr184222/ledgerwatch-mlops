import numpy as np
import pandas as pd

FEATURES = ['amount','hour','account_age_days','transactions_24h','foreign','distance_km']

def generate(n=5000, seed=42, drift=False):
    """Independent chronological synthetic records; labels are invented, not fraud evidence."""
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame({
        'amount':rng.lognormal(4.1 if not drift else 5.1,1.05,n).clip(1,15000),
        'hour':rng.integers(0,24,n),
        'account_age_days':rng.integers(1,1800,n),
        'transactions_24h':rng.poisson(3 if not drift else 8,n),
        'foreign':rng.binomial(1,.10 if not drift else .40,n),
        'distance_km':rng.exponential(35 if not drift else 190,n).clip(0,5000)})
    logit = (-5.2 + 1.1*(frame.amount>250) + 1.3*(frame.hour<5) + 1.6*(frame.account_age_days<60)
             + .25*frame.transactions_24h + 1.7*frame.foreign + 1.4*(frame.distance_km>120))
    frame['label'] = rng.binomial(1,1/(1+np.exp(-logit)))
    frame['event_time'] = pd.date_range('2025-01-01',periods=n,freq='h').astype(str)
    frame['transaction_id'] = [f'SYN-{seed}-{i:05d}' for i in range(n)]
    return frame
