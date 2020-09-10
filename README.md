# docker-drawio-renderer
Dockerized service exposing a REST interface for rendering draw.io diagrams into images.

## What it does

[Diagrams.net](https://diagrams.net) has added [command-line options](https://j2r2b.github.io/2019/08/06/drawio-cli.html) to [Draw.io Desktop](https://github.com/jgraph/drawio-desktop) which allow you to automate converting diagrams into images.  This is great!

Unfortunately, Draw.io desktop is an Electron-based application, and cannot execute without first installing a huge number of dependencies, including a GUI environment such as X11 within which it can run.  This makes it difficult to integrate into other services such as Jenkins build pipelines.

This package puts Draw.io Desktop into a Docker container along with all of its dependencies and a simple HTTP REST server, allowing you to easily call it from other services regardless of platform or language.

Due to the large number of dependencies, the container produced is very big; I welcome contributions to trim its size down!  In the meantime, at least all of this bloat is hidden inside this one container and won't affect the rest of your services.

## Running

```
docker run -d -p 5000:5000 --shm-size=1g tomkludy/drawio-renderer:latest
```

Note the `--shm-size` parameter; this determines the maximum memory that can be used during diagram rendering.  If omitted, the default is 256mb.  If you hit out-of-memory errors (HTTP status code 413), try increasing the value of this parameter.

## API

Start up the container and navigate to the `/docs` route on it; for example: `http://localhost:5000/docs`

Alternatively, plug [openapi.yaml](openapi.yaml) into your favorite OpenAPI renderer such as https://editor.swagger.io to see the API details.

## Shout outs

This would not have been possible without [this post](https://github.com/jgraph/drawio-desktop/issues/127#issuecomment-520053181) from [Joel Martin](https://github.com/kanaka); he resolved most of the hard issues.

_Note: contrary to the linked comment thread, this approach does NOT require `--cap-add SYS_ADMIN`._
