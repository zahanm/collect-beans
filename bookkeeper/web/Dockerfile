# syntax=docker/dockerfile:1

FROM node:lts
ENV NODE_ENV production

ENV YARN_VERSION 1.22.19
RUN yarn policies set-version $YARN_VERSION

WORKDIR /app

COPY ["package.json", "yarn.lock", "./"]

RUN yarn install --frozen-lockfile --link-duplicates --non-interactive
RUN yarn global add serve

COPY . .

RUN yarn build

EXPOSE 3000
ENTRYPOINT [ "serve", "build/" ]
