# bluesky-in-a-box 

Bluesky services in docker containers, for use in Wright Group experimental orchestration.

## ports

This application uses the following ports:

| port  | protocol | content          |
| :---- | :------- | :--------------- |
| 27017 | mongo    | databroker       |
| 6379  | redis    | re-manager redis |
| 5555  | zmq      | re-manager       |
| 60610 | json     | queueserver      |

## prepare

```
$ apt install docker.io
$ apt install docker-compose
```

## start 

```
$ sudo docker-compose up --build
```

Go to http://localhost:60610/docs to see queueserver api.
