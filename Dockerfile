FROM php:8.1-fpm-alpine
WORKDIR /app
COPY . /app
RUN docker-php-ext-install pdo_mysql
RUN mkdir -p /app/storage && chown -R www-data:www-data /app/storage
EXPOSE 9000
CMD ["php-fpm"]
