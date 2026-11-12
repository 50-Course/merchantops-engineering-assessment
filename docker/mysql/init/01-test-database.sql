-- Allow the MerchantOps application user to manage its
-- dedicated Django test database.
--
-- MySQL treats underscores as wildcards in privilege patterns,
-- so escape the underscore in test_merchantops.

GRANT ALL PRIVILEGES
ON `test\_merchantops`.*
TO 'merchantops'@'%';
