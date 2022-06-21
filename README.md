# Website Monitor System 
Website Monitor System (WMS) monitors the state of websites and logs it into a database. It is an exercise of asyncio. The system consists of two parts:
- Producer - monitors websites listed in `websites.json` asynchronously and sends the status packages to Kafka topic `website_check`. It is in the `producer` folder
- Consumer - asynchronously consumes packages and sends them to `results_log` table of `check_results` database. It is in the `consumer` folder
there are `shared` folder - a small library to store check results and `resources` folder - where all user defined data is kept.

WMS relies on Aiven Kafka and Aiven PostrgeSQL. The following instruction will describe how to set everything up.

## Setting up Aiven services
To get things running you'll need:
1. A running Aiven Kafka with `website_check` topic. Three partitions are recomended to feel the power of async. That could easily be done from the web interface.
2. A running PostgreSQL database with the name `results_log`. We'll use a default ***avnadmin*** username. 
First to set up database run 
```
CREATE DATABASE check_results
    WITH 
    OWNER = avnadmin
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    CONNECTION LIMIT = -1;
```
To create a table
```
CREATE TABLE IF NOT EXISTS public.results_log
(
    "timestamp" numeric NOT NULL,
    url text NOT NULL,
    result text NOT NULL,
    response_time real,
    regex_result boolean
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.results_log
    OWNER to avnadmin;
```
## Setting up Website Monitor System

Producer and Consumer run in separate environments and are built independently. This could be done on different environments. They use the same Kafka access keys, that are stored in `resources` folder as well as lists of websites to check and PostgreSQL username and passwords.
1. To build Producer and Consumer you'll need `Python 3.10` (there are some fancy type hinting features one cannot refuse to employ). Once you have cloned current repository to your local machine please install `Pipenv`
```
pip install --user pipenv
```
2. In `producer` and `consumer` folders run 
```
pipenv install
```
3. Download yur Kafka access keys (also from web interface) and put them into the directory `\resources\certificates`. Or you could use a directory of your choice and specify it in `\resources\kafka_certificates.json`.


- `service.key` - Access Key
- `service.cert` - Access Certificate
- `ca.pem` -  CA Certificate

And enter your Kafaka service uri in `service_uri`
```
{
  "service_uri":"<your address>.aivencloud.com:<port>",
  "ca_path":"path/to/ca.pem",
  "key_path": "path/to/service.key",
  "cert_path": "path/to/service.cert"
}
```
4. Enter your PostgreSQL credentials to  `\resources\db_access_data.json`
- `user` - PostgreSQL User name, by default avnadmin (if the SQL frome above is not modified - that's username you need)
- `password` - PostgreSQL password
- `host` - your Aiven PostgreSQL address (will look like ******.aivencloud.com",
- `port` - your Aiven PostgreSQL port. The default is `27160` but it is advised to check.
```
{
  "user":"avnadmin",
  "password":"your_password",
  "host":"<your address>.aivencloud.com",
  "port":"<port>"
}
```
5. Look through website lists 
Websites to be checked are stored in `\resources\websites.json`
There is an example of a **very** diverse group of blocked sites that are monitored by Citizen Lab -  https://github.com/citizenlab/test-lists


You could set up your own website using syntax:

- `[<url>,<regex>]` where `url` is an adress and `regex` is Python re regular expression rule to check on the site body. Currently it works only on the first 500 kb of the body. 

- `[<url>]` if you don't need regex check

6. Run Consumer with `pipenv run python consumer.py`. You will see the results of website checks in the form of `[<site>:<result>]`
7. Run Producer with `pipenv run python producer.py`. You will see the results consumed from Kafka and sent to PostgreSQL. An interesting experiment would be to use one consumer instead of three
8. Stop running Consumer or Producer with `CTRL+C`

Be warned: if you are using a provided dataset from an unprepared network two things might start happening: some websites will stop responding thinking you are attacking them, and your provider might begin blocking your requests.

## Testing
Testing is done with async pyTest library. For Producer and Consumer please run 
```
pipenv run pytest --log-cli-level=10
```
Cli is to make it less boring as it will take some time to run those.
## Attribution
- Multiple problems with logging were resolved in this thread (thanks to Helgi Borg)
https://stackoverflow.com/questions/57730749/python-logging-two-loggers-two-log-files-how-to-configure-logging-ini
- `aiohttp` `aiokafka` and `aiopg` are brilliant libraries created by multiple contributors. Many credits are to Andrew Svetlov https://github.com/asvetlov
