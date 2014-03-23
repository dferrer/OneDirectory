CREATE TABLE IF NOT EXISTS account (
  user_id   varchar(20),
  password  varchar(20),
  auto_sync boolean,
  primary key(user_id)
);

CREATE TABLE IF NOT EXISTS file (
  path    varchar(100),
  user_id varchar(20),
  size    int(7),
  primary key(path)
);

CREATE TABLE IF NOT EXISTS log (
  user_id varchar(20),
  path    varchar(100),
  time    timestamp,
  action  text,
  primary key(user_id, path, time, action)
);