from quantopian.algorithm import order_optimal_portfolio
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import SimpleMovingAverage
from quantopian.pipeline.filters import QTradableStocksUS
import quantopian.optimize as opt

def initialize(context):
    # Schedule our rebalance function to run at the start of
    # each week, when the market opens.
    schedule_function(
        my_rebalance,
        date_rules.week_start(),
        time_rules.market_open()
    )

    # Create our pipeline and attach it to our algorithm.
    my_pipe = make_pipeline()
    attach_pipeline(my_pipe, 'my_pipeline')

def make_pipeline():
    """
    Create our pipeline.
    """

    # Base universe set to the QTradableStocksUS.
    base_universe = QTradableStocksUS()

    # 10-day close price average.
    mean_10 = SimpleMovingAverage(
        inputs=[USEquityPricing.close],
        window_length=10,
        mask=base_universe
    )

    # 30-day close price average.
    mean_30 = SimpleMovingAverage(
        inputs=[USEquityPricing.close],
        window_length=30,
        mask=base_universe
    )

    percent_difference = (mean_10 - mean_30) / mean_30

    # Filter to select securities to short.
    shorts = percent_difference.top(75)

    # Filter to select securities to long.
    longs = percent_difference.bottom(75)

    # Filter for all securities that we want to trade.
    securities_to_trade = (shorts | longs)

    return Pipeline(
        columns={
            'longs': longs,
            'shorts': shorts
        },
        screen=(securities_to_trade),
    )

def compute_target_weights(context, data):
    """
    Compute ordering weights.
    """

    # Initialize empty target weights dictionary.
    # This will map securities to their target weight.
    weights = {}

    # If there are securities in our longs and shorts lists,
    # compute even target weights for each security.
    if context.longs and context.shorts:
        long_weight = 0.5 / len(context.longs)
        short_weight = -0.5 / len(context.shorts)
    else:
        return weights

    # Exit positions in our portfolio if they are not
    # in our longs or shorts lists.
    for security in context.portfolio.positions:
        if security not in context.longs and security not in context.shorts and data.can_trade(security):
            weights[security] = 0

    for security in context.longs:
        weights[security] = long_weight

    for security in context.shorts:
        weights[security] = short_weight

    return weights

def before_trading_start(context, data):
    """
    Get pipeline results.
    """

    # Gets our pipeline output every day.
    pipe_results = pipeline_output('my_pipeline')

    # Go long in securities for which the 'longs' value is True,
    # and check if they can be traded.
    context.longs = []
    for sec in pipe_results[pipe_results['longs']].index.tolist():
        if data.can_trade(sec):
            context.longs.append(sec)

    # Go short in securities for which the 'shorts' value is True,
    # and check if they can be traded.
    context.shorts = []
    for sec in pipe_results[pipe_results['shorts']].index.tolist():
        if data.can_trade(sec):
            context.shorts.append(sec)

def my_rebalance(context, data):
    """
    Rebalance weekly.
    """

    # Calculate target weights to rebalance
    target_weights = compute_target_weights(context, data)

    # If we have target weights, rebalance our portfolio
    if target_weights:
        order_optimal_portfolio(
            objective=opt.TargetWeights(target_weights),
            constraints=[],
        )