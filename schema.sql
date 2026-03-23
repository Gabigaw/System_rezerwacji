CREATE TABLE salon (
    salon_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    address VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(100)
);

CREATE TABLE hairdresser (
    hairdresser_id INT AUTO_INCREMENT PRIMARY KEY,
    salon_id INT NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(100),
    specialization VARCHAR(100),
    status VARCHAR(30) DEFAULT 'active',
    CONSTRAINT fk_hairdresser_salon
        FOREIGN KEY (salon_id) REFERENCES salon(salon_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

CREATE TABLE client (
    client_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE service (
    service_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    duration_minutes INT NOT NULL,
    base_price DECIMAL(10,2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE hairdresser_service (
    hairdresser_id INT NOT NULL,
    service_id INT NOT NULL,
    custom_price DECIMAL(10,2),
    PRIMARY KEY (hairdresser_id, service_id),
    CONSTRAINT fk_hs_hairdresser
        FOREIGN KEY (hairdresser_id) REFERENCES hairdresser(hairdresser_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_hs_service
        FOREIGN KEY (service_id) REFERENCES service(service_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE TABLE time_slot (
    slot_id INT AUTO_INCREMENT PRIMARY KEY,
    salon_id INT NOT NULL,
    hairdresser_id INT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'available',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_slot_salon
        FOREIGN KEY (salon_id) REFERENCES salon(salon_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_slot_hairdresser
        FOREIGN KEY (hairdresser_id) REFERENCES hairdresser(hairdresser_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

CREATE TABLE appointment (
    appointment_id INT AUTO_INCREMENT PRIMARY KEY,
    slot_id INT NOT NULL UNIQUE,
    client_id INT NOT NULL,
    service_id INT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    booking_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    confirmed_at DATETIME NULL,
    cancelled_at DATETIME NULL,
    cancellation_reason VARCHAR(255),
    notes TEXT,
    CONSTRAINT fk_appointment_slot
        FOREIGN KEY (slot_id) REFERENCES time_slot(slot_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_appointment_client
        FOREIGN KEY (client_id) REFERENCES client(client_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_appointment_service
        FOREIGN KEY (service_id) REFERENCES service(service_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

CREATE TABLE payment (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    appointment_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(30) NOT NULL,
    payment_status VARCHAR(30) NOT NULL DEFAULT 'pending',
    paid_at DATETIME NULL,
    transaction_reference VARCHAR(100),
    CONSTRAINT fk_payment_appointment
        FOREIGN KEY (appointment_id) REFERENCES appointment(appointment_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE TABLE waiting_queue (
    queue_id INT AUTO_INCREMENT PRIMARY KEY,
    slot_id INT NOT NULL,
    client_id INT NOT NULL,
    service_id INT NOT NULL,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    position INT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'waiting',
    CONSTRAINT fk_queue_slot
        FOREIGN KEY (slot_id) REFERENCES time_slot(slot_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_queue_client
        FOREIGN KEY (client_id) REFERENCES client(client_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_queue_service
        FOREIGN KEY (service_id) REFERENCES service(service_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

CREATE TABLE queue_offer (
    offer_id INT AUTO_INCREMENT PRIMARY KEY,
    queue_id INT NOT NULL,
    slot_id INT NOT NULL,
    offered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    response_status VARCHAR(30) NOT NULL DEFAULT 'pending',
    CONSTRAINT fk_offer_queue
        FOREIGN KEY (queue_id) REFERENCES waiting_queue(queue_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_offer_slot
        FOREIGN KEY (slot_id) REFERENCES time_slot(slot_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);