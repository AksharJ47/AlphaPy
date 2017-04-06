################################################################################
#
# Package   : AlphaPy
# Module    : portfolio
# Created   : July 11, 2013
#
# Copyright 2017 ScottFree Analytics LLC
# Mark Conway & Robert D. Scott II
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
################################################################################


#
# Imports
#

from alphapy.frame import Frame
from alphapy.frame import frame_name
from alphapy.frame import read_frame
from alphapy.frame import write_frame
from alphapy.globs import MULTIPLIERS, SSEP
from alphapy.globs import Orders
from alphapy.space import Space

import logging
import math
import numpy as np
from pandas import DataFrame
from pandas import date_range
from pandas import Series


#
# Initialize logger
#

logger = logging.getLogger(__name__)


#
# Function portfolio_name
#

def portfolio_name(group_name, tag):
    """
    Return the name of the portfolio.

    Parameters
    ----------
    group_name : str
        The group represented in the portfolio.
    tag : str
        A unique identifier.

    Returns
    -------
    port_name : str
        Portfolio name.

    """
    port_name = '.'.join([group_name, tag, "portfolio"])
    return port_name


#
# Class Portfolio
#

class Portfolio():
    """Create a new portfolio with a unique name. All portfolios
    are stored in ``Portfolio.portfolios``.

    Parameters
    ----------
    group_name : str
        The group represented in the portfolio.
    tag : str
        A unique identifier.
    space : alphapy.Space, optional
        Namespace for the portfolio.
    maxpos : int, optional
        The maximum number of positions.
    posby : str, optional
        The denominator for position sizing.
    kopos : int, optional
        The number of positions to kick out from the portfolio.
    koby : str, optional
        The "kick out" criteria. For example, a ``koby`` value
        of '-profit' means the three least profitable positions
        will be closed.
    restricted : bool, optional
        If ``True``, then the portfolio is limited to a maximum
        number of positions ``maxpos``.
    weightby : str, optional
        The weighting variable to balance the portfolio, e.g.,
        by closing price, by volatility, or by any column.
    startcap : float, optional
        The amount of starting capital.
    margin : float, optional
        The amount of margin required, expressed as a fraction.
    mincash : float, optional
        Minimum amount of cash on hand, expressed as a fraction
        of the total portfolio value.
    fixedfrac : float, optional
        The fixed fraction for any given position.
    maxloss : float, optional
        Stop loss for any given position.

    Attributes
    ----------
    portfolios : dict
        Class variable for storing all known portfolios
    value : float
        Class variable for storing all known portfolios
    netprofit : float
        Net profit ($) since previous valuation.
    netreturn : float
        Net return (%) since previous valuation
    totalprofit : float
        Total profit ($) since inception.
    totalreturn : float
        Total return (%) since inception.

    """

    # class variable to track all portfolios

    portfolios = {}

    # __new__
    
    def __new__(cls,
                group_name,
                tag,
                space = Space(),
                maxpos = 10,
                posby = 'close',
                kopos = 0,
                koby = '-profit',
                restricted = False,
                weightby = 'quantity',
                startcap = 100000,
                margin = 0.5,
                mincash = 0.2,
                fixedfrac = 0.1,
                maxloss = 0.1):
        # create portfolio name
        pn = portfolio_name(group_name, tag)
        if not pn in Portfolio.portfolios:
            return super(Portfolio, cls).__new__(cls)
        else:
            logger.info("Portfolio %s already exists", pn)
    
    # __init__
    
    def __init__(self,
                 group_name,
                 tag,
                 space = Space(),
                 maxpos = 10,
                 posby = 'close',
                 kopos = 0,
                 koby = '-profit',
                 restricted = False,
                 weightby = 'quantity',
                 startcap = 100000,
                 margin = 0.5,
                 mincash = 0.2,
                 fixedfrac = 0.1,
                 maxloss = 0.1):
        # initialization
        self.group_name = group_name
        self.tag = tag
        self.space = space
        self.positions = {}
        self.startdate = None
        self.enddate = None
        self.npos = 0
        self.maxpos = maxpos
        self.posby = posby
        self.kopos = kopos
        self.koby = koby
        self.restricted = restricted
        self.weightby = weightby
        self.weights = []
        self.startcap = startcap
        self.cash = startcap
        self.margin = margin
        self.mincash = mincash
        self.fixedfrac = fixedfrac
        self.maxloss = maxloss
        self.value = startcap
        self.netprofit = 0.0
        self.netreturn = 0.0
        self.totalprofit = 0.0
        self.totalreturn = 0.0
        # add portfolio to portfolios list
        pn = portfolio_name(group_name, tag)
        Portfolio.portfolios[pn] = self

    # __str__

    def __str__(self):
        return portfolio_name(self.group_name, self.tag)


#
# Class Position
#

class Position:
    """Create a new position in the portfolio.

    Parameters
    ----------
    group_name : str
        The group represented in the portfolio.
    tag : str
        A unique identifier.
    space : alphapy.Space, optional
        Namespace for the portfolio.
    maxpos : int, optional
        The maximum number of positions.
    posby : str, optional
        The denominator for position sizing.
    kopos : int, optional
        The number of positions to kick out from the portfolio.
    koby : str, optional
        The "kick out" criteria. For example, a ``koby`` value
        of '-profit' means the three least profitable positions
        will be closed.
    restricted : bool, optional
        If ``True``, then the portfolio is limited to a maximum
        number of positions ``maxpos``.
    weightby : str, optional
        The weighting variable to balance the portfolio, e.g.,
        by closing price, by volatility, or by any column.
    startcap : float, optional
        The amount of starting capital.
    margin : float, optional
        The amount of margin required, expressed as a fraction.
    mincash : float, optional
        Minimum amount of cash on hand, expressed as a fraction
        of the total portfolio value.
    fixedfrac : float, optional
        The fixed fraction for any given position.
    maxloss : float, optional
        Stop loss for any given position.

    Attributes
    ----------
    group_name : str
        The group represented in the portfolio.
    tag : str
        A unique identifier.
    space : alphapy.Space, optional
        Namespace for the portfolio.
    maxpos : int, optional
        The maximum number of positions.
    posby : str, optional
        The denominator for position sizing.
    kopos : int, optional
        The number of positions to kick out from the portfolio.
    koby : str, optional
        The "kick out" criteria. For example, a ``koby`` value
        of '-profit' means the three least profitable positions
        will be closed.
    restricted : bool, optional
        If ``True``, then the portfolio is limited to a maximum
        number of positions ``maxpos``.
    weightby : str, optional
        The weighting variable to balance the portfolio, e.g.,
        by closing price, by volatility, or by any column.
    startcap : float, optional
        The amount of starting capital.
    margin : float, optional
        The amount of margin required, expressed as a fraction.
    mincash : float, optional
        Minimum amount of cash on hand, expressed as a fraction
        of the total portfolio value.
    fixedfrac : float, optional
        The fixed fraction for any given position.
    maxloss : float, optional
        Stop loss for any given position.

    """
    
    # __init__
    
    def __init__(self,
                 portfolio,
                 name,
                 opendate):
        space = portfolio.space
        self.date = opendate
        self.name = name
        self.status = 'opened'
        self.mpos = 'flat'
        self.quantity = 0
        self.price = 0.0
        self.value = 0.0
        self.profit = 0.0
        self.netreturn = 0.0
        self.opened = opendate
        self.held = 0
        self.costbasis = 0.0
        self.trades = []
        self.ntrades = 0
        self.pdata = Frame.frames[frame_name(name, space)].df
        self.multiplier = MULTIPLIERS[space.subject]

    # __str__
    
    def __str__(self):
        return self.name


#
# Class Trade
#

class Trade:
    """Create a new portfolio with a unique name. All portfolios
    are stored in ``Portfolio.portfolios``.

    Parameters
    ----------
    group_name : str
        The group represented in the portfolio.
    space : alphapy.Space, optional
        Namespace for the portfolio.
    maxpos : int, optional
        The maximum number of positions.
    posby : str, optional
        The denominator for position sizing.
    kopos : int, optional
        The number of positions to kick out from the portfolio.
    koby : str, optional
        The "kick out" criteria. For example, a ``koby`` value
        of '-profit' means the three least profitable positions
        will be closed.
    restricted : bool, optional
        If ``True``, then the portfolio is limited to a maximum
        number of positions ``maxpos``.
    weightby : str, optional
        The weighting variable to balance the portfolio, e.g.,
        by closing price, by volatility, or by any column.
    startcap : float, optional
        The amount of starting capital.
    margin : float, optional
        The amount of margin required, expressed as a fraction.
    mincash : float, optional
        Minimum amount of cash on hand, expressed as a fraction
        of the total portfolio value.
    fixedfrac : float, optional
        The fixed fraction for any given position.
    maxloss : float, optional
        Stop loss for any given position.

    Attributes
    ----------
    states : list
        Net profit ($) since previous valuation.

    """
    
    states = ['name', 'order', 'quantity', 'price']

    # __init__

    def __init__(self,
                 name,
                 order,
                 quantity,
                 price,
                 tdate):
        self.name = name
        self.order = order
        self.quantity = float(quantity)
        self.price = float(price)
        self.tdate = tdate


#
# Function add_position
#

def add_position(p, name, pos):
    r"""Add a position to a portfolio by name.

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    if name not in p.positions:
        p.positions[name] = pos


#
# Function remove_position
#

def remove_position(p, name):
    r"""Remove a position from a portfolio by name.

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    del p.positions[name]


#
# Function valuate_position
#

def valuate_position(position, tdate):
    r"""Valuate the position based on the trade list.

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----

    An Example of Cost Basis:

    Position 1:  +100 * 10 =  1,000
    Position 2:  +200 * 15 =  3,000
    Position 3:  -500 * 20 = 10,000
                 ----        ------
    Total Shares  800        14,000

    Cost Basis: 14,000 / 800 = 17.5
    Position is -200 (net short) @ 17.5

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    # get current price
    pdata = position.pdata
    if tdate in pdata.index:
        cp = float(pdata.ix[tdate]['close'])
        # start valuation
        multiplier = position.multiplier
        netpos = 0
        tts = 0     # total traded shares
        ttv = 0     # total traded value
        totalprofit = 0.0
        for trade in position.trades:
            tq = trade.quantity
            netpos = netpos + tq
            tts = tts + abs(tq)
            tp = trade.price
            pfactor = tq * multiplier
            cv = pfactor * cp
            cvabs = abs(cv)
            ttv = ttv + cvabs
            ev = pfactor * tp
            totalprofit = totalprofit + cv - ev
        position.quantity = netpos
        position.price = cp
        position.value = abs(netpos) * multiplier * cp
        position.profit = totalprofit
        position.costbasis = ttv / tts
        position.netreturn = totalprofit / cvabs - 1.0


#
# Function update_position
#

def update_position(position, trade):
    r"""Update the position status and valuate it.

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    position.trades.append(trade)
    position.ntrades = position.ntrades + 1
    position.date = trade.tdate
    position.held = trade.tdate - position.opened
    valuate_position(position, trade.tdate)
    if position.quantity > 0:
        position.mpos = 'long'
    if position.quantity < 0:
        position.mpos = 'short'
    return position


#
# Function close_position
#

def close_position(p, position, tdate):
    r"""Close the position and remove it from the portfolio.

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    pq = position.quantity
    # if necessary, put on an offsetting trade
    if pq != 0:
        tradesize = -pq
        position.date = tdate
        pdata = position.pdata
        cp = pdata.ix[tdate]['close']
        newtrade = Trade(position.name, tradesize, cp, tdate)
        update_portfolio(p, position, newtrade, tradesize)
        position.quantity = 0
    position.status = 'closed'
    remove_position(p, position.name)

    
#
# Function deposit_portfolio
#

def deposit_portfolio(p, cash, tdate):
    r"""Deposit cash into a given portfolio.

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    p.cash = p.cash + cash
    valuate_portfolio(p, tdate)
    return p.value


#
# Function withdraw_portfolio
#

def withdraw_portfolio(p, cash, tdate):
    r"""Withdraw cash from a given portfolio

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    currentcash = p.cash
    availcash = currentcash - (p.mincash * p.value)
    if cash > availcash:
        logger.info("Withdrawal of %s would exceed reserve amount", cash)
    else:
        p.cash = currentcash - cash
        valuate_portfolio(p, tdate)
    return p.value


#
# Function update_portfolio
#

def update_portfolio(p, pos, trade, allocation):
    r"""Update the portfolio positions

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    # update position
    ppq = abs(pos.quantity)
    update_position(pos, trade)
    cpq = abs(pos.quantity)
    npq = cpq - ppq
    # update portfolio
    p.date = trade.tdate
    multiplier = pos.multiplier
    cv = trade.price * multiplier * npq
    p.cash -= cv


#
# Function delete_portfolio
#

def delete_portfolio(p):
    r"""Delete the portfolio, closing all positions.

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    positions = p.positions
    for key in positions:
        close_position(p, positions[key])
    del p


#
# Function balance
#

def balance(p, tdate, cashlevel):
    r"""Balance the portfolio using a weighting variable.

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    currentcash = p.cash
    mincash = p.mincash
    weightby = p.weightby
    if not weightby:
        weightby = 'close'
    valuate_portfolio(p, tdate)
    pvalue = p.value - cashlevel * p.value
    positions = p.positions
    bdata = np.ones(len(positions))
    # get weighting variable values
    if weightby[0] == "-":
        invert = True
        weightby = weightby[1:]
    else:
        invert = False
    attrs = filter(lambda aname: not aname.startswith('_'), dir(positions[0]))
    for i, pos in enumerate(positions):
        if weightby in attrs:
            estr = '.'.join('pos', weightby)
            bdata[i] = eval(estr)
        else:
            bdata[i] = pos.pdata.ix[tdate][weightby]
    if invert:
        bweights = (2 * bdata.mean() - bdata) / sum(bdata)
    else:
        bweights = bdata / sum(bdata)
    # rebalance
    for i, pos in enumerate(positions):
        multiplier = pos.multiplier
        bdelta = bweights[i] * pvalue - pos.value
        cp = pos.pdata.ix[tdate]['close']
        tradesize = math.trunc(bdelta / cp)
        ntv = abs(tradesize) * cp * multiplier
        if tradesize > 0:
            order = Orders.le
        if tradesize < 0:
            order = Orders.se
        exec_trade(p, pos.name, order, tradesize, cp, tdate)
        p.cash = currentcash + bdelta - ntv


#
# Function kick_out
#

def kick_out(p, tdate):
    r"""Trim the portfolio based on filter criteria.

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    positions = p.positions
    maxpos = p.maxpos
    numpos = len(positions)
    kovalue = np.zeros(numpos)
    koby = p.koby
    if not koby:
        koby = 'profit'
    if koby[0] == "-":
        descending = True
        koby = koby[1:]
    else:
        descending = False
    attrs = filter(lambda aname: not aname.startswith('_'), dir(positions[0]))
    for i, pos in enumerate(positions):
        if koby in attrs:
            estr = '.'.join('pos', koby)
            kovalue[i] = eval(estr)
        else:
            kovalue[i] = pos.pdata.ix[tdate][koby]
    koorder = np.argsort(np.argsort(kovalues))
    if descending:
        koorder = [i for i in reversed(koorder)]
    if numpos >= maxpos:
        freepos = numpos - maxpos + p.kopos
        # close the top freepos positions
        if freepos > 0:
            for i in range(freepos):
                close_position(p, positions[koorder[i]], tdate)


#
# Function stop_loss
#

def stop_loss(p, tdate):
    r"""Trim the portfolio based on stop-loss criteria.

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    positions = p.positions
    maxloss = p.maxloss
    for key in positions:
        pos = positions[key]
        nr = pos.netreturn
        if nr <= -maxloss:
            close_position(p, pos, tdate)


#
# Function valuate_portfolio
#

def valuate_portfolio(p, tdate):
    r"""Value the portfolio based on the current positions.

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    positions = p.positions
    poslen = len(positions)
    vpos = [0] * poslen
    p.weights = [0] * poslen
    posenum = enumerate(positions)
    # save the current portfolio value
    prev_value = p.value
    # compute the total portfolio value
    value = p.cash
    for i, key in posenum:
        pos = positions[key]
        valuate_position(pos, tdate)
        vpos[i] = pos.value
        value = value + vpos[i]
    p.value = value
    # now compute the weights
    for i, key in posenum:
        p.weights[i] = vpos[i] / p.value
    # update portfolio stats
    p.netprofit = p.value - prev_value
    p.netreturn = p.value / prev_value - 1.0
    p.totalprofit = p.value - p.startcap
    p.totalreturn = p.value / p.startcap - 1.0


#
# Function allocate_trade
#

def allocate_trade(p, pos, trade):
    r"""Determine the trade allocation for a given portfolio.

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    cash = p.cash
    margin = p.margin
    mincash = p.mincash
    restricted = p.restricted
    if restricted:
        kick_out(p, trade.tdate)
        stop_loss(p, trade.tdate)
    multiplier = pos.multiplier
    qpold = pos.quantity
    qtrade = trade.quantity
    qpnew = qpold + qtrade
    allocation = abs(qpnew) - abs(qpold)
    addedvalue = trade.price * multiplier * abs(allocation)
    if restricted:
        cashreserve = mincash * cash
        freemargin = (cash - cashreserve) / margin
        if addedvalue > freemargin:
            logger.info("Required free margin: %d < added value: %d",
                        freemargin, addedvalue)
            allocation = 0
        else:
            freecash = cash - addedvalue
            if freecash < 0:
                p.cash = cash + freecash
    return allocation


#
# Function exec_trade
#

def exec_trade(p, name, order, quantity, price, tdate):
    r"""Execute a trade within a portfolio

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    # see if the position already exists
    if name in p.positions:
        pos = p.positions[name]
        newpos = False
    else:
        pos = Position(p, name, tdate)
        newpos = True
    # check the dynamic position sizing variable
    if not p.posby:
        tsize = quantity
    else:
        if order == Orders.le or order == Orders.se:
            pf = Frame.frames[frame_name(name, p.space)].df
            cv = float(pf.ix[tdate][p.posby])
            tsize = math.trunc((p.value * p.fixedfrac) / cv)
            if quantity < 0:
                tsize = -tsize
        else:
            tsize = -pos.quantity
    # instantiate and allocate the trade
    newtrade = Trade(name, order, tsize, price, tdate)
    allocation = allocate_trade(p, pos, newtrade)
    if allocation != 0:
        # create a new position if necessary
        if newpos:
            add_position(p, name, pos)
            p.npos += 1
        # update the portfolio
        update_portfolio(p, pos, newtrade, allocation)
        # if net position is zero, then close the position
        pflat = pos.quantity == 0
        if pflat:
            close_position(p, pos, tdate)
            p.npos -= 1
    else:
        logger.info("Trade Allocation for %s is 0", name)
    # return trade size
    return tsize


#
# Function gen_portfolio
#

def gen_portfolio(model, system, group, tframe,
                  startcap=100000, posby='close'):
    r"""Create a portfolio from a trades frame.

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    describe : type
        Explanation of return value named `describe`.

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """

    logger.info("Creating Portfolio for System %s", system)

    # Unpack the model data.

    directory = model.specs['directory']
    extension = model.specs['extension']
    separator = model.specs['separator']

    # Create the portfolio.

    gname = group.name
    gspace = group.space
    gmembers = group.members
    ff = 1.0 / len(gmembers)

    p = Portfolio(gname,
                  system,
                  gspace,
                  startcap = startcap,
                  posby = posby,
                  restricted = False,
                  fixedfrac = ff)
    if not p:
        logger.error("Error creating Portfolio")

    # Build pyfolio data from the trades frame.

    start = tframe.index[0]
    end = tframe.index[-1]
    trange = np.unique(tframe.index.map(lambda x: x.date().strftime('%Y-%m-%d'))).tolist()
    drange = date_range(start, end).map(lambda x: x.date().strftime('%Y-%m-%d'))

    # Initialize return, position, and transaction data.

    rs = []
    pcols = list(gmembers)
    pcols.extend(['cash'])
    pf = DataFrame(index=drange, columns=pcols).fillna(0.0)
    ts = []

    # Iterate through the date range, updating the portfolio.
    for d in drange:
        # process today's trades
        if d in trange:
            trades = tframe.ix[d]
            if isinstance(trades, Series):
                trades = DataFrame(trades).transpose()
            for t in trades.iterrows():
                tdate = t[0]
                row = t[1]
                tsize = exec_trade(p, row['name'], row['order'], row['quantity'], row['price'], tdate)
                if tsize != 0:
                    ts.append((d, [tsize, row['price'], row['name']]))
                else:
                    logger.info("Trade could not be executed for %s", row['name'])
        # iterate through current positions
        positions = p.positions
        pfrow = pf.ix[d]
        for key in positions:
            pos = positions[key]
            if pos.quantity > 0:
                value = pos.value
            else:
                value = -pos.value
            pfrow[pos.name] = value
        pfrow['cash'] = p.cash
        # update the portfolio returns
        valuate_portfolio(p, d)
        rs.append((d, [p.netreturn]))

    # Create systems directory path

    system_dir = SSEP.join([directory, 'systems'])

    # Create and record the returns frame for this system.

    logger.info("Recording Returns Frame")
    rspace = Space(system, 'returns', gspace.fractal)
    rf = DataFrame.from_items(rs, orient='index', columns=['return'])
    rfname = frame_name(gname, rspace)
    write_frame(rf, system_dir, rfname, extension, separator,
                index=True, index_label='date')
    del rspace

    # Record the positions frame for this system.

    logger.info("Recording Positions Frame")
    pspace = Space(system, 'positions', gspace.fractal)
    pfname = frame_name(gname, pspace)
    write_frame(pf, system_dir, pfname, extension, separator,
                index=True, index_label='date')
    del pspace

    # Create and record the transactions frame for this system.

    logger.info("Recording Transactions Frame")
    tspace = Space(system, 'transactions', gspace.fractal)
    tf = DataFrame.from_items(ts, orient='index', columns=['amount', 'price', 'symbol'])
    tfname = frame_name(gname, tspace)
    write_frame(tf, system_dir, tfname, extension, separator,
                index=True, index_label='date')
    del tspace

    # Return the portfolio.
    return p
