from copy import copy
import datetime
from dataclasses import dataclass, field

from sysexecution.orders.base_orders import (
    no_order_id,
    no_children,
    no_parent,
    orderType, resolve_multi_leg_price_to_single_price)
from sysexecution.orders.base_orders import Order, resolve_inputs_to_order
from sysexecution.trade_qty import tradeQuantity
from sysexecution.orders.contract_orders import contractOrder
from sysexecution.orders.instrument_orders import instrumentOrder

from sysobjects.production.tradeable_object import  instrumentStrategy, futuresContract, futuresContractStrategy

from syscore.genutils import none_to_object, object_to_none
from syscore.objects import fill_exceeds_trade, success


class brokerOrderType(orderType):
    def allowed_types(self):
        return ['market', 'limit', 'balance_trade']

market_order_type = brokerOrderType('market')
limit_order_type = brokerOrderType('limit')
balance_order_type = brokerOrderType('balance_trade')

class brokerOrder(Order):
    def __init__(
        self,
        *args,
        fill: tradeQuantity=None,
            filled_price: float = None,
            fill_datetime: datetime.datetime = None,
        leg_filled_price: list = [],
        locked: bool=False,
        order_id: int=no_order_id,
        parent: int=no_parent,
        children: list=no_children,
        active: bool=True,
        order_type: brokerOrderType = brokerOrderType("market"),

        algo_used: str="",
        algo_comment: str="",

        limit_price: float=None,
        submit_datetime: datetime.datetime=None,
        side_price: float=None,
        mid_price: float=None,
        offside_price: float =None,

        roll_order: bool = False,

        broker: str="",
        broker_account: str="",
        broker_clientid: str="",
        broker_permid: str = "",
        broker_tempid: str = "",
        commission: float=0.0,
        manual_fill: bool=False,
        **kwargs_ignored
    ):
        """

        :param args: Either a single argument 'strategy/instrument/contract_id' str, or strategy, instrument, contract_id; followed by trade
        i.e. brokerOrder(strategy, instrument, contractid, trade,  **kwargs) or 'strategy/instrument/contract_id', trade, type, **kwargs)

        Contract_id can either be a single str or a list of str for spread orders, all YYYYMM
        If expressed inside a longer string, separate contract str by '_'

        i.e. brokerOrder('a strategy', 'an instrument', '201003', 6,  **kwargs)
         same as brokerOrder('a strategy/an instrument/201003', 6,  **kwargs)
        brokerOrder('a strategy', 'an instrument', ['201003', '201406'], [6,-6],  **kwargs)
          same as brokerOrder('a strategy/an instrument/201003_201406', [6,-6],  **kwargs)
        :param fill:  fill done so far, list of int
        :param locked: bool, is order locked
        :param order_id: int, my ref number
        :param modification_status: NOT USED
        :param modification_quantity: NOT USED
        :param parent: int or not supplied, parent order
        :param children: list of int or not supplied, child order ids (FUNCTIONALITY NOT USED HERE)
        :param active: bool, is order active or has been filled/cancelled
        :param algo_used: Name of the algo I used to generate the order
        :param order_type: market or limit order (other types may be supported in future)
        :param limit_price: if relevant, float
        :param filled_price: float
        :param submit_datetime: datetime
        :param fill_datetime: datetime
        :param side_price: Price on the 'side' we are submitting eg offer if buying, when order submitted
        :param mid_price: Average of bid and offer when we are submitting
        :param algo_comment: Any comment made by the algo, eg 'Aggressive', 'Passive'...
        :param broker: str, name of broker
        :param broker_account: str, brokerage account
        :param broker_clientid: int, client ID used to generate order
        :param commission: float
        :param broker_permid: Brokers permanent ref number
        :param broker_tempid: Brokers temporary ref number
        :param manual_fill: bool, was fill entered manually rather than being picked up from IB

        """

        key_arguments = from_broker_order_args_to_resolved_args(args,
                                            fill=fill,
                                            filled_price=filled_price,
                                            leg_filled_price=leg_filled_price,
                                            mid_price=mid_price,
                                            side_price=side_price,
                                            offside_price=offside_price)

        resolved_trade = key_arguments.trade
        resolved_fill = key_arguments.fill
        resolved_filled_price = key_arguments.filled_price
        tradeable_object = key_arguments.tradeable_object
        leg_filled_price = key_arguments.leg_filled_price
        mid_price = key_arguments.mid_price
        side_price = key_arguments.side_price
        offside_price = key_arguments.offside_price

        if len(resolved_trade) == 1:
            calendar_spread_order = False
        else:
            calendar_spread_order = True


        order_info = dict(
            algo_used=algo_used,
            submit_datetime=submit_datetime,
            limit_price=limit_price,
            manual_fill=manual_fill,
            calendar_spread_order=calendar_spread_order,
            side_price=side_price,
            mid_price=mid_price,
            offside_price = offside_price,
            algo_comment=algo_comment,
            broker=broker,
            broker_account=broker_account,
            broker_permid=broker_permid,
            broker_tempid=broker_tempid,
            broker_clientid=broker_clientid,
            commission=commission,
            roll_order=roll_order,
            leg_filled_price = leg_filled_price
        )

        super().__init__(tradeable_object,
                        trade= resolved_trade,
                        fill = resolved_fill,
                        filled_price= resolved_filled_price,
                        fill_datetime = fill_datetime,
                        locked = locked,
                        order_id=order_id,
                        parent = parent,
                        children= children,
                        active=active,
                        order_type=order_type,
                        **order_info
                        )


    @property
    def strategy_name(self):
        return self.tradeable_object.strategy_name

    @property
    def instrument_code(self):
        return self.tradeable_object.instrument_code

    @property
    def contract_date(self):
        return self.tradeable_object.contract_date

    @property
    def instrument_strategy(self) -> instrumentStrategy:
        return self.tradeable_object.instrument_strategy

    @property
    def contract_date_key(self):
        return self.tradeable_object.contract_date_key

    @property
    def limit_price(self):
        return self.order_info["limit_price"]

    @limit_price.setter
    def limit_price(self, limit_price):
        self.order_info["limit_price"] = limit_price



    @property
    def algo_used(self):
        return self.order_info["algo_used"]


    @property
    def calendar_spread_order(self):
        return self.order_info["calendar_spread_order"]


    @property
    def submit_datetime(self):
        return self.order_info["submit_datetime"]

    @submit_datetime.setter
    def submit_datetime(self, submit_datetime):
        self.order_info["submit_datetime"] = submit_datetime

    @property
    def manual_fill(self):
        return bool(self.order_info["manual_fill"])

    @manual_fill.setter
    def manual_fill(self, manual_fill):
        self.order_info["manual_fill"] = manual_fill

    @property
    def side_price(self):
        return self.order_info["side_price"]

    @property
    def mid_price(self):
        return self.order_info["mid_price"]

    @property
    def offside_price(self):
        return self.order_info["offside_price"]


    @property
    def algo_comment(self):
        return self.order_info["algo_comment"]

    @algo_comment.setter
    def algo_comment(self, comment):
        self.order_info["algo_comment"] = comment

    @property
    def broker(self):
        return self.order_info["broker"]

    @property
    def broker_account(self):
        return self.order_info["broker_account"]

    @property
    def broker_permid(self):
        return self.order_info["broker_permid"]

    @broker_permid.setter
    def broker_permid(self, permid):
        self.order_info["broker_permid"] = permid

    @property
    def broker_clientid(self):
        return self.order_info["broker_clientid"]

    @broker_clientid.setter
    def broker_clientid(self, broker_clientid):
        self.order_info["broker_clientid"] = broker_clientid

    @property
    def broker_tempid(self):
        return self.order_info["broker_tempid"]

    @broker_tempid.setter
    def broker_tempid(self, broker_tempid):
        self.order_info["broker_tempid"] = broker_tempid

    @property
    def commission(self):
        return self.order_info["commission"]

    @commission.setter
    def commission(self, comm):
        self.order_info["commission"] = comm

    @property
    def futures_contract(self):
        return futuresContract(instrument_object=self.instrument_code, contract_date_object=self.contract_date)

    @property
    def leg_filled_price(self):
        return self.order_info["leg_filled_price"]

    @leg_filled_price.setter
    def leg_filled_price(self, leg_filled_price: list):
        self.order_info["leg_filled_price"] = list


    @classmethod
    def from_dict(instrumentOrder, order_as_dict):
        trade = order_as_dict.pop("trade")
        key = order_as_dict.pop("key")
        fill = order_as_dict.pop("fill")
        filled_price = order_as_dict.pop("filled_price")
        fill_datetime = order_as_dict.pop("fill_datetime")

        locked = order_as_dict.pop("locked")
        order_id = none_to_object(order_as_dict.pop("order_id"), no_order_id)
        parent = none_to_object(order_as_dict.pop("parent"), no_parent)
        children = none_to_object(order_as_dict.pop("children"), no_children)
        active = order_as_dict.pop("active")
        order_type = brokerOrderType(order_as_dict.pop("order_type", None))

        order_info = order_as_dict

        order = brokerOrder(
            key,
            trade,
            fill=fill,
            locked=locked,
            order_id=order_id,
            parent=parent,
            children=children,
            active=active,
            filled_price=filled_price,
            fill_datetime=fill_datetime,
            order_type=order_type,
            **order_info
        )

        return order


    def log_with_attributes(self, log):
        """
        Returns a new log object with broker_order attributes added

        :param log: logger
        :return: log
        """
        broker_order = self
        new_log = log.setup(
            strategy_name=broker_order.strategy_name,
            instrument_code=broker_order.instrument_code,
            contract_order_id=object_to_none(broker_order.parent, no_parent),
            broker_order_id=object_to_none(broker_order.order_id, no_order_id),
        )

        return new_log

    def add_execution_details_from_matched_broker_order(
            self, matched_broker_order):
        fill_qty_okay = self.trade.fill_less_than_or_equal_to_desired_trade(
            matched_broker_order.fill
        )
        if not fill_qty_okay:
            return fill_exceeds_trade
        self.fill_order(
            matched_broker_order.fill,
            filled_price=matched_broker_order.filled_price,
            fill_datetime=matched_broker_order.fill_datetime,
        )
        self.commission = matched_broker_order.commission
        self.broker_permid = matched_broker_order.broker_permid
        self.algo_comment = matched_broker_order.algo_comment
        self.leg_filled_price = matched_broker_order.leg_filled_price

        return success


def create_new_broker_order_from_contract_order(
    contract_order: contractOrder,
    order_type: brokerOrderType=brokerOrderType('market'),
    limit_price: float=None,
    submit_datetime: datetime.datetime=None,
    side_price: float=None,
    mid_price: float=None,
    offside_price: float = None,
    algo_comment: str="",
    broker: str="",
    broker_account: str="",
    broker_clientid: str="",
    broker_permid: str="",
    broker_tempid: str="",
) -> brokerOrder:


    broker_order = brokerOrder(
        contract_order.key,
        contract_order.trade,
        parent=contract_order.order_id,
        algo_used=contract_order.algo_to_use,
        order_type=order_type,
        limit_price=limit_price,
        side_price=side_price,
        offside_price=offside_price,
        mid_price=mid_price,
        broker=broker,
        broker_account=broker_account,
        broker_clientid=broker_clientid,
        submit_datetime=submit_datetime,
        algo_comment=algo_comment,
        broker_permid=broker_permid,
        broker_tempid=broker_tempid,
        roll_order=contract_order.roll_order,
        manual_fill=contract_order.manual_fill

    )

    return broker_order

## Not very pretty but only used for diagnostic TCA
class brokerOrderWithParentInformation(brokerOrder):
    @classmethod
    def create_augemented_order(self, order: brokerOrder, instrument_order: instrumentOrder, contract_order: contractOrder):

        # Price when the trade was generated. We use the contract order price since
        #  the instrument order price may refer to a different contract
        order.parent_reference_price = contract_order.reference_price

        # when the trade was originally generated, this is the instrument order
        # used to measure effects of delay eg from close
        order.parent_reference_datetime =instrument_order.reference_datetime

        # instrument order prices may refer to a different contract
        # so we use the contract order limit
        order.parent_limit_price = contract_order.limit_price

        order.buy_or_sell = order.trade.buy_or_sell()

        return order




@dataclass
class brokerOrderKeyArguments():
    tradeable_object: futuresContractStrategy
    trade: tradeQuantity
    fill: tradeQuantity = None
    filled_price: float = None
    leg_filled_price: list = field(default_factory=list)
    mid_price: float = None
    side_price: float = None
    offside_price: float = None

    def resolve_inputs_to_order_with_key_arguments(self):

        ## We do this because the next line turns the price into a float
        ##   We want to keep it in case any multileg information is there
        ##   Which will end up in leg_filled_price
        original_filled_price = copy(self.filled_price)
        resolved_trade, resolved_fill, resolved_filled_price = resolve_inputs_to_order(trade=self.trade,
                                                                                       fill=self.fill,
                                                                                       filled_price=self.filled_price)

        ## Now ensure that all prices have correct format
        leg_filled_price, mid_price, side_price, offside_price = \
            calculate_prices_with_possible_legs(trade=resolved_trade,
                                            leg_filled_price=self.leg_filled_price,
                                            mid_price=self.mid_price,
                                            side_price=self.side_price,
                                            offside_price=self.offside_price,
                                            original_filled_price=original_filled_price)

        self.filled_price = resolved_filled_price
        self.fill = resolved_fill
        self.trade = resolved_trade
        self.leg_filled_price = leg_filled_price
        self.mid_price = mid_price
        self.side_price = side_price
        self.offside_price = offside_price

    def sort_inputs_by_contract_date_order(self):
        sort_order = self.tradeable_object.sort_idx_for_contracts()
        self.trade.sort_with_idx(sort_order)
        self.fill.sort_with_idx(sort_order)

        self.tradeable_object.sort_contracts_with_idx(sort_order)


def from_broker_order_args_to_resolved_args(args: tuple, fill: tradeQuantity, filled_price: float,
                                            leg_filled_price: list = [],
                                            mid_price: float = None,
                                            side_price: float = None,
                                            offside_price: float = None
                                            ) -> brokerOrderKeyArguments:

    # different ways of specififying tradeable object
    key_arguments = split_broker_order_args(args,
                                            fill=fill,
                                            filled_price=filled_price,
                                            leg_filled_price=leg_filled_price,
                                            mid_price=mid_price,
                                            side_price=side_price,
                                            offside_price=offside_price)

    # ensure everything has the right type
    key_arguments.resolve_inputs_to_order_with_key_arguments()

    # ensure contracts and lists all match
    key_arguments.sort_inputs_by_contract_date_order()

    return key_arguments


def split_broker_order_args(args: tuple, fill: tradeQuantity, filled_price: float,
                            leg_filled_price: list = [],
                            mid_price: float = None,
                            side_price: float = None,
                            offside_price: float = None)\
        -> brokerOrderKeyArguments:

    if len(args) == 2:
        tradeable_object = futuresContractStrategy.from_key(args[0])
        trade = args[1]
    elif len(args) == 4:
        strategy = args[0]
        instrument = args[1]
        contract_id = args[2]
        trade = args[3]
        tradeable_object = futuresContractStrategy(
            strategy, instrument, contract_id
        )
    else:
        raise Exception(
            "brokerOrder(strategy, instrument, contractid, trade,  **kwargs) or ('strategy/instrument/contract_order_id', trade, **kwargs) "
        )

    key_arguments = brokerOrderKeyArguments(tradeable_object=tradeable_object, trade=trade, fill=fill,
                                              filled_price=filled_price,
                                            leg_filled_price=leg_filled_price,
                                            mid_price=mid_price,
                                            side_price=side_price,
                                            offside_price=offside_price)

    return key_arguments




def calculate_prices_with_possible_legs(trade: tradeQuantity,
                                        leg_filled_price,
                                        mid_price,
                                        side_price,
                                        offside_price,
                                        original_filled_price
                                        ) -> (list, float,float):

    ## Leg filled price: In older trades, not specified, in newer trades is a list length of fill
    ## Mid price: In older trades, list length of fill, in newer trades is a float
    ## Side price: In older trades, list length of fill, in newer trades is a float
    ## Offside price: In older trades, list length of fill, in newer trades is a float
    ## Filled price: In older trades list length of fill, in newer trades is a float

    ## We don't change 'filled_price' here, this is done elsewhere

    if type(original_filled_price) is float:
        ## Newer style, can't modify
        pass

    elif original_filled_price is None:
        pass

    elif leg_filled_price==[]:
        ## Older style without leg filled price. Filled price is probably a list or list like. Save the filled prices here or we lose them
        leg_filled_price = list(copy(original_filled_price))
    else:
        ## Not sure
        raise Exception("Not sure how to parse order")

    ## Convert old style to new style
    mid_price = resolve_multi_leg_price_to_single_price(trade_list=trade, price_list=mid_price)
    side_price = resolve_multi_leg_price_to_single_price(trade_list=trade, price_list=side_price)
    offside_price = resolve_multi_leg_price_to_single_price(trade_list=trade, price_list=offside_price)

    return leg_filled_price, mid_price, side_price, offside_price