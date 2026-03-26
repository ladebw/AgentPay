from prometheus_client import Counter, Histogram, Gauge
import time

# Counters
SPONSORED_TX_COUNT = Counter(
    "agentpay_sponsored_transactions_total",
    "Total sponsored transactions",
    ["chain", "agent_tier"],
)

SPONSOR_GAS_COST = Histogram(
    "agentpay_sponsor_gas_cost_usd",
    "Gas cost of sponsored transactions in USD",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
)

SPONSOR_FAILURE_COUNT = Counter(
    "agentpay_sponsor_failures_total", "Total sponsorship failures", ["reason"]
)

# Gauges
SPONSOR_ELIGIBLE_AGENTS = Gauge(
    "agentpay_sponsor_eligible_agents",
    "Number of agents currently eligible for sponsorship",
)

SPONSOR_DAILY_SPENT_USD = Gauge(
    "agentpay_sponsor_daily_spent_usd",
    "Total USD spent on sponsorship today",
    ["agent_id"],
)


def record_sponsored_transaction(chain: str, agent_tier: str, gas_cost_usd: float):
    """Record metrics for a successful sponsored transaction."""
    SPONSORED_TX_COUNT.labels(chain=chain, agent_tier=agent_tier).inc()
    if gas_cost_usd is not None:
        SPONSOR_GAS_COST.observe(gas_cost_usd)


def record_sponsorship_failure(reason: str):
    """Record a sponsorship failure."""
    SPONSOR_FAILURE_COUNT.labels(reason=reason).inc()


def update_eligible_agents(count: int):
    """Update gauge with number of eligible agents."""
    SPONSOR_ELIGIBLE_AGENTS.set(count)


def update_daily_spent(agent_id: str, amount_usd: float):
    """Update daily spent for an agent."""
    SPONSOR_DAILY_SPENT_USD.labels(agent_id=agent_id).set(amount_usd)
