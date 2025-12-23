IMAGE_NAME=discord-music-bot
CONTAINER_NAME=discord-music-bot
ENV_FILE=.env

.PHONY: build run stop logs shell clean

up: stop build run

build:
	docker build -t $(IMAGE_NAME) .

run:
	docker run  \
		--name $(CONTAINER_NAME) \
		--env-file $(ENV_FILE) \
		$(IMAGE_NAME)

stop:
	docker stop $(CONTAINER_NAME) || true
	docker rm $(CONTAINER_NAME) || true