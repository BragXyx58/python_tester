CREATE DATABASE TestSystem;
USE TestSystem;

CREATE TABLE Users (
    [id] INT PRIMARY KEY IDENTITY,
    [username] VARCHAR(50) NOT NULL UNIQUE,
    [password_hash] VARCHAR(255) NOT NULL,
    [is_admin] BIT NOT NULL DEFAULT 0
);

CREATE TABLE Tests (
    [id] INT PRIMARY KEY IDENTITY,
    [title] VARCHAR(100) NOT NULL,
    [description] VARCHAR(500)
);

CREATE TABLE Questions (
    [id] INT PRIMARY KEY IDENTITY,
    [test_id] INT NOT NULL,
    [question_text] VARCHAR(500) NOT NULL,
    FOREIGN KEY ([test_id]) REFERENCES Tests([id]) ON DELETE CASCADE
);

CREATE TABLE Answers (
    [id] INT PRIMARY KEY IDENTITY,
    [question_id] INT NOT NULL,
    [answer_text] VARCHAR(300) NOT NULL,
    [is_correct] BIT NOT NULL,
    FOREIGN KEY ([question_id]) REFERENCES Questions([id]) ON DELETE CASCADE
);

CREATE TABLE Results (
    [id] INT PRIMARY KEY IDENTITY,
    [user_id] INT NOT NULL,
    [test_id] INT NOT NULL,
    [result_date] DATETIME DEFAULT GETDATE(),
    [correct_answers] INT NOT NULL,
    [total_questions] INT NOT NULL,
    [score_percent] FLOAT NOT NULL,
    FOREIGN KEY ([user_id]) REFERENCES Users([id]),
    FOREIGN KEY ([test_id]) REFERENCES Tests([id])
);

CREATE TABLE AnswerLogs (
    [id] INT PRIMARY KEY IDENTITY,
    [user_id] INT NOT NULL,
    [test_id] INT NOT NULL,
    [question_id] INT NOT NULL,
    [selected_answer_id] INT NOT NULL,
    [is_correct] BIT NOT NULL,
    [timestamp] DATETIME DEFAULT GETDATE(),
    FOREIGN KEY ([user_id]) REFERENCES Users([id]),
    FOREIGN KEY ([test_id]) REFERENCES Tests([id]),
    FOREIGN KEY ([question_id]) REFERENCES Questions([id]),
    FOREIGN KEY ([selected_answer_id]) REFERENCES Answers([id])
);

INSERT INTO Tests ([title], [description])
VALUES ('HTTP Status Codes Basics', 'Основы кодов состояния HTTP: от 1xx до 5xx');

INSERT INTO Questions (test_id, question_text)
VALUES 
(1, 'Код который подходит под описание: "OK — успешный запрос"'),
(1, 'Код который подходит под описание: "Not Found — не найдено"'),
(1, 'Код который подходит под описание: "Internal Server Error"'),
(1, 'Код который подходит под описание: "Moved Permanently"');

INSERT INTO Answers (question_id, answer_text, is_correct) VALUES
(1, '200', 1),
(1, '404', 0),
(1, '500', 0),
(1, '301', 0);

INSERT INTO Answers (question_id, answer_text, is_correct) VALUES
(2, '200', 0),
(2, '404', 1),
(2, '500', 0),
(2, '301', 0);


INSERT INTO Answers (question_id, answer_text, is_correct) VALUES
(3, '200', 0),
(3, '404', 0),
(3, '500', 1),
(3, '301', 0);

INSERT INTO Answers (question_id, answer_text, is_correct) VALUES
(4, '200', 0),
(4, '404', 0),
(4, '500', 0),
(4, '301', 1);

INSERT INTO Users (username, password_hash, is_admin)
VALUES ('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 1);

SELECT * FROM AnswerLogs
SELECT * FROM Results
SELECT * FROM Users
SELECT * FROM Tests
SELECT * FROM Questions
SELECT * FROM Answers

DROP TABLE Tests
DROP TABLE Questions
DROP TABLE Answers
DROP TABLE Results
DROP TABLE AnswerLogs


