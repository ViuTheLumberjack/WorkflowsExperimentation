# Workflows

Project to test the behaviour of a service running on a docker container with concurrent requests via JMeter

## Instructions

### 1. Build with Maven

To build services, run the command:

```sh
mvn clean package
```

### 2. Starting containers with Docker Compose

Edit the ``docker-compose.yml`` file to instantiate services in independent containers, assigning appropriate resources and unique ports. Then start the containers by executing the following command:


```sh
docker-compose up -d
```

### 3. Test execution

To run tests with JMeter, use the `run-test.py` script:

```sh
python run-test.py
```

### 4. Processes test results

To process test results, use the script `process-test.py`:

```sh
python process-test.py
```

### Customising the test configuration

The file `utility.py` can be edited to customise the test configuration runs.

## Note

Make sure you have installed all the necessary dependencies for Maven, Docker, Python and JMeter before running the above commands.