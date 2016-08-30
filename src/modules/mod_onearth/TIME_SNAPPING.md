#mod\_onearth Date Snapping

###How OnEarth Date Snapping Works

Not all imagery layers will have data on a per-day basis. Some, for
example, may have one new image for every 3-day or 6-month interval.

In these cases, it can be difficult and inconvenient for a client to get
imagery if they don’t know the exact dates those images are available.

To make things easier, OnEarth allows layers to be configured with
multiple time periods, and will “snap” an image request to the closest
available date with data.

For example, say a particular product only has 1 image for every 3-day
period, starting 2012-01-01. Normally, a request for an image from
2012-01-01 or 2012-01-04 would return imagery, but a request for
2012-01-02 or 2012-01-05 would not.

When a layer is configured with time periods in OnEarth, mod\_onearth
will snap the otherwise invalid dates to the closest imagery before that
date. So if a client requests data from 2012-01-02 OnEarth will serve
data from 2012-01-01. And for 2012-01-05, it will “snap” to 2012-01-04.

This works the same for yearly products. Say a product only generates
one image per year, and that image is delivered on April 1. All requests
for dates between 2015-04-01 and 2016-03-01 will snap to 2015-04-01 –
the first date of that time period. A request for 2016-06-17 will snap
to 2016-04-01.

=====
###Configuring Layer Time Periods

Time periods for a certain layer can be configured in the layer
configuration XML file (the one processed by the `oe_configure_layer`
script). Each separate period is contained in a &lt;Time> tag.

The string format for each time period is as follows:

`ISO 8601 Start Date / ISO 8601 First Date of the Last Time Period / P
(Interval Length) (Interval Unit in Y,M,D,H,M,S)`

So, for a period starting on 6/17/2000, having imagery every 7 days, and
with a final time period that starts on 2001-11-11 the configuration
string would be:

`<Time>2000-06-17/2001-11-11/P7D</Time>`

and for a yearly product starting 2000-10-31 and having a final period
that starts on 2007-06-25, the string would be:

`<Time>2000-10-31/2007-06-25/P1Y</Time>`

------

Note that oe\_configure\_layer can also detect time periods based on the
filenames in the imagery cache directory or entries in a subdaily
layer’s .zdb file. For more information, consult [time detection](https://github.com/nasa-gibs/onearth/blob/master/doc/time_detection.md).

**Unless otherwise specified OnEarth assumes a 1-day time period for non-subdaily layers and a 1-second time period for subdaily ones.**

Note that multiple, overlapping time periods with start and end dates
can be configured for a specific layer. So,

`<Time>2000-01-01/2016-01-01/P1Y</Time>`

`<Time>2014-06-17/2014-06-26/P3D</Time>`

is acceptable.

======

###Some More Snapping Rules

OnEarth follows a few rules when date snapping that are important to
know.

**Time periods are evaluated from the latest start date backwards to the
earliest start date.** So in this example:

`<Time>2000-01-01/2016-01-01/P1Y</Time>`

`<Time>2014-06-17/2014-06-26/P3D</Time>`

**The second period would be evaluated first.** If the requested date lies
within that period, the imagery is served according to the rules of that
time period (so 2014-06-21 would snap to 2014-06-17 and not 2014-01-01).
The first period is not evaluated, even though its time span overlaps
the second.

**Dates only snap backwards.** They always snap to the nearest interval
before the request date, hence:

**Request dates earlier than the start date of the period aren’t snapped.** If no periods containing the request date are found, the
empty tile is served.

**Dates beyond the end date of the time period will snap backwards to the end date, but only if they are within one interval of the end date.**

For example, say the time period is `2011-01-01/2012-01-01/P7D`. The
date **2012-01-06** will snap backwards to **2012-01-01**, since it’s
within 7 days of the end date of the period. However, a request date of
**2012-01-07** will result in an empty tile, because it is beyond the
last interval of the period.

=====
###Additional Notes about Subdaily (Time) Snapping:

**For legacy subdaily layers (with individual files for each granule),
time/date snapping works same as with dates.** Times are snapped
backwards as long as they are within the start date and the end of the
last interval in the time period. 

**Note that, with subdaily layers, the
letter “M” stands for minutes and not months, as it does with daily
layers.**

**For z-level subdaily layers, dates/times are not snapped.** Any
request for a granule that does not exist currently results in a WMTS
error.

=====
###WMS Time Snapping:

**Time snapping also works via WMS request with the onearth-mapserver packaged installed.** mod_oems and mod_oemstime must be configured for the endpoint for time snapping to occur.

**A Tiled-WMS endpoint must exist for mod_oemstime to leverage the mod_onearth time snapping functions.**

**Time snapping will work with WMS requests with multiple layers.** If the requested date is invalid for a layer, that layer will be ignored by the request.