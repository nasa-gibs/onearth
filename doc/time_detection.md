# Time Detection

The [OnEarth Layer Configuration tool](../src/layer_config/README.md) has the ability to detect time ranges for a given layer.  This is accomplished by the use of special keywords in the [layer configuration file](config_layer.md).

## Time Element Options

1) Known date range in ISO 8601 format with start time, end time, and duration.
```xml
<Time>2013-01-01/2014-03-28/P1D</Time>
```

2) Automatically detect the start time, end time, and duration.
```xml
<Time>DETECT</Time>
```

3) Automatically detect only the start time.
```xml
<Time>DETECT/2014-03-28/P1D</Time>
```

4) Automatically detect only the end time.
```xml
<Time>2013-01-01/DETECT/P1D</Time>
```

5) Automatically detect the start and end times but use a predetermined period.
```xml
<Time>DETECT/DETECT/P5D</Time>
```

6) Automatically detect the start and end times but use a predetermined period; create multiple date ranges if breaks are detected.
```xml
<Time>DETECT/P5D</Time>
```

Multiple `<Time>` elements are allowed.
```xml
<Time>2012-01-01/2012-12-31/P1D</Time>
<Time>2013-01-01/2013-12-31/P2D</Time>
<Time>2014-01-01/DETECT/P1D</Time>
```

Sub-daily periods are also supported.
```xml
<Time>2000-01-01T00:45:00Z/2014-12-31T23:55:00Z/PT5M30S</Time>
<Time>2000-01-01T00:00:00Z/DETECT/PT5M</Time>
```

Note: The period detection is determined by the first three intervals in the image archive for the given layer.  Time detection may not be accurate if there are less than four files or if they are not continuous.