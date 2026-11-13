### Performance and Investigation Report

My approach to performance optimization was to look beyond just the application code. I wanted to understand how much work the application was doing, how it interacted with the database, and how much data was being transferred to the client.

I used Django Silk alongside the console and the browser's developer tools to investigate these areas. Django Silk helped me identify repeated SQL queries and inspect request performance, while the console helped me understand the existing data and query behaviour. I used the Network tab to inspect HTTP requests and measure response transfer sizes.

I started with the application code, particularly the product list and product editor views. Both endpoints were making unnecessary database queries when retrieving related records. I improved how these records were fetched using `select_related` and `prefetch_related`, reducing the number of database round trips without changing the existing API response structure.

After these changes, the product list went from 30 SQL queries to 6, while the product editor went from 10 to 7 for the sampled product. I also tested the editor with products containing different numbers of variants, including a product with 50 variants, to verify that the query count remained constant.

At this point, I had reduced the amount of database work required to serve a request, but I wanted to see if there was still room for improvement beyond the application and database layers.

The next thing I looked at was the network. The product editor returns a considerable amount of data for products with many variants. Even though the database queries had been optimized, the server still needed to transfer that data to the client.

This led me to consider response compression. Rather than removing fields from the response or changing the API contract, I enabled Django's GZip middleware and measured the same JSON response before and after compression using the browser's Network tab.

For a product with 50 variants, the response transfer size dropped from 11.56 KB to 1.67 KB, approximately an 85.6% reduction, while the uncompressed JSON response remained 11.23 KB.

The idea was to reduce unnecessary work at each layer: how the application retrieves data, how often it communicates with the database, and how much data it transfers over the network.

For a visual walkthrough of my performance investigation, I have included timestamped screenshots showing the findings, before-and-after measurements, and optimization results in the [screenshots](./screenshots/) directory.
