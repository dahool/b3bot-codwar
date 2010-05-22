-- phpMyAdmin SQL Dump
-- Generation Time: May 22, 2010
-- 

-- --------------------------------------------------------

-- Existing pre v1.3.1 client table needs to be updated: 
ALTER TABLE `aliases` ADD COLUMN `ip` VARCHAR( 16 ) NOT NULL default '';
      
CREATE TABLE IF NOT EXISTS disabledcmd (
  id int(11) NOT NULL auto_increment,
  cmd varchar(50) NOT NULL,
  until int(11) NOT NULL,
  PRIMARY KEY  (id),
  UNIQUE KEY cmd (cmd)
) TYPE=MyISAM ;
