-- Создание таблицы пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    nickname VARCHAR(255),
    is_subscribed BOOLEAN DEFAULT FALSE,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы категорий товаров
CREATE TABLE IF NOT EXISTS categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT
);

-- Создание таблицы товаров
CREATE TABLE IF NOT EXISTS products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    strength VARCHAR(50),
    image_url VARCHAR(255),
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

-- Создание таблицы магазинов
CREATE TABLE IF NOT EXISTS stores (
    store_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address VARCHAR(255) NOT NULL
);

-- Создание таблицы наличия товаров в магазинах
CREATE TABLE IF NOT EXISTS inventory (
    inventory_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    store_id INT,
    quantity INT NOT NULL DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (store_id) REFERENCES stores(store_id)
);

-- Создание таблицы заказов
CREATE TABLE IF NOT EXISTS orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('pending', 'paid', 'delivered', 'cancelled') DEFAULT 'pending',
    total_amount DECIMAL(10, 2) NOT NULL,
    store_id INT,
    delivery_address TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (store_id) REFERENCES stores(store_id)
);

-- Создание таблицы элементов заказа
CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT,
    product_id INT,
    quantity INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- Заполнение таблицы категорий
INSERT INTO categories (name, description) VALUES
('Одноразовые устройства', 'Одноразовые электронные сигареты различных брендов'),
('Устройства', 'Многоразовые электронные сигареты и POD-системы'),
('Жидкости легкие', 'Жидкости с низким содержанием никотина (до 12 мг)'),
('Жидкости крепкие', 'Жидкости с высоким содержанием никотина (от 12 мг)'),
('Картриджи', 'Сменные картриджи для POD-систем'),
('Испарители', 'Сменные испарители для электронных сигарет');

-- Заполнение таблицы магазинов
INSERT INTO stores (name, address) VALUES
('Puff Smoke на Дзержинского', 'ул. Дзержинского, 16'),
('Puff Smoke на Степана Разина', 'ул. Степана Разина, 60д');

-- Заполнение таблицы товаров
-- Одноразовые устройства
INSERT INTO products (category_id, name, description, price, strength, image_url) VALUES
(1, 'HQD Cuvie Plus', 'Одноразовая электронная сигарета HQD Cuvie Plus на 1200 затяжек', 850.00, '50 мг', 'hqd_cuvie_plus.jpg'),
(1, 'Elf Bar 1500', 'Одноразовая электронная сигарета Elf Bar на 1500 затяжек', 950.00, '50 мг', 'elf_bar_1500.jpg'),
(1, 'Puff Bar XXL', 'Одноразовая электронная сигарета Puff Bar XXL на 1600 затяжек', 1000.00, '50 мг', 'puff_bar_xxl.jpg');

-- Устройства
INSERT INTO products (category_id, name, description, price, strength, image_url) VALUES
(2, 'Smoant Pasito 2', 'POD-система Smoant Pasito 2 с регулировкой мощности', 3500.00, NULL, 'smoant_pasito_2.jpg'),
(2, 'Vaporesso XROS 3', 'POD-система Vaporesso XROS 3 с аккумулятором 1000 mAh', 2800.00, NULL, 'vaporesso_xros_3.jpg'),
(2, 'GeekVape Aegis Boost', 'POD-мод GeekVape Aegis Boost с защитой от влаги и ударов', 4200.00, NULL, 'geekvape_aegis_boost.jpg');

-- Жидкости легкие
INSERT INTO products (category_id, name, description, price, strength, image_url) VALUES
(3, 'Jam Monster Apple', 'Жидкость со вкусом яблочного джема', 1200.00, '3 мг', 'jam_monster_apple.jpg'),
(3, 'Bad Drip Don\'t Care Bear', 'Жидкость со вкусом мармеладных мишек', 1300.00, '6 мг', 'bad_drip_bear.jpg'),
(3, 'Nasty Juice Cushman', 'Жидкость со вкусом манго', 1100.00, '6 мг', 'nasty_juice_cushman.jpg');

-- Жидкости крепкие
INSERT INTO products (category_id, name, description, price, strength, image_url) VALUES
(4, 'Husky Salt Mint', 'Солевая жидкость со вкусом мяты', 650.00, '20 мг', 'husky_salt_mint.jpg'),
(4, 'Brusko Salt Strawberry', 'Солевая жидкость со вкусом клубники', 700.00, '20 мг', 'brusko_salt_strawberry.jpg'),
(4, 'Nic Salt Tobacco', 'Солевая жидкость со вкусом табака', 750.00, '35 мг', 'nic_salt_tobacco.jpg');

-- Картриджи
INSERT INTO products (category_id, name, description, price, strength, image_url) VALUES
(5, 'JUUL Pods Mint', 'Картриджи для JUUL со вкусом мяты, 4 шт', 1200.00, '18 мг', 'juul_pods_mint.jpg'),
(5, 'Vaporesso XROS Pod', 'Сменный картридж для Vaporesso XROS', 450.00, NULL, 'vaporesso_xros_pod.jpg'),
(5, 'Smoant Pasito Cartridge', 'Сменный картридж для Smoant Pasito', 500.00, NULL, 'smoant_pasito_cartridge.jpg');

-- Испарители
INSERT INTO products (category_id, name, description, price, strength, image_url) VALUES
(6, 'GeekVape Mesh Coil', 'Сетчатый испаритель для GeekVape Aegis Boost', 350.00, NULL, 'geekvape_mesh_coil.jpg'),
(6, 'Vaporesso GT Coil', 'Испаритель для атомайзеров Vaporesso', 300.00, NULL, 'vaporesso_gt_coil.jpg'),
(6, 'SMOK RPM Mesh Coil', 'Сетчатый испаритель для SMOK RPM', 380.00, NULL, 'smok_rpm_mesh_coil.jpg');

-- Заполнение таблицы наличия товаров
-- Наличие в магазине на Дзержинского
INSERT INTO inventory (product_id, store_id, quantity) VALUES
(1, 1, 15), (2, 1, 10), (3, 1, 8),
(4, 1, 5), (5, 1, 7), (6, 1, 3),
(7, 1, 20), (8, 1, 15), (9, 1, 12),
(10, 1, 25), (11, 1, 18), (12, 1, 22),
(13, 1, 30), (14, 1, 25), (15, 1, 20),
(16, 1, 40), (17, 1, 35), (18, 1, 30);

-- Наличие в магазине на Степана Разина
INSERT INTO inventory (product_id, store_id, quantity) VALUES
(1, 2, 12), (2, 2, 8), (3, 2, 10),
(4, 2, 4), (5, 2, 6), (6, 2, 2),
(7, 2, 18), (8, 2, 14), (9, 2, 10),
(10, 2, 22), (11, 2, 16), (12, 2, 20),
(13, 2, 28), (14, 2, 22), (15, 2, 18),
(16, 2, 38), (17, 2, 32), (18, 2, 28); 