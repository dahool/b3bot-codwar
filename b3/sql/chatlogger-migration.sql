RENAME TABLE chatlog TO chatlog_old;

CREATE TABLE chatlog (
  id int(11) unsigned NOT NULL auto_increment,
  msg_time int(10) unsigned NOT NULL,
  msg_type enum('ALL','TEAM','PM') NOT NULL,
  client_id int(11) unsigned NOT NULL,
  client_name varchar(32) NOT NULL,
  client_team tinyint(1) NOT NULL,
  msg varchar(528) NOT NULL,
  target_id int(11) unsigned default NULL,
  target_name varchar(32) default NULL,
  target_team tinyint(1) default NULL,
  PRIMARY KEY  (id),
  KEY client (client_id),
  KEY target (target_id),
  KEY time_add (msg_time)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

INSERT INTO chatlog (msg_time, msg_type, client_id, client_name, client_team, msg, target_id, target_name, target_team)
SELECT time_add, IF(INSTR(target,'TEAM') > 0,'TEAM',IF(INSTR(target,'CLIENT') > 0,'PM','ALL')), client_id, '-', '-', data, 
IF(INSTR(target,'CLIENT') > 0, SUBSTRING(target, 10, INSTR(target,']')-10), null),
IF(INSTR(target,'CLIENT') > 0, SUBSTRING(target, INSTR(target,'-')+2), null),
null FROM chatlog_old;
