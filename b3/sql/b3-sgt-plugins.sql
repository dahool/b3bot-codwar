SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;

--
-- Base de datos: `b3`
--

--
-- Estructura de tabla para la tabla `auditlog`
--

CREATE TABLE IF NOT EXISTS `auditlog` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `command` varchar(20) DEFAULT NULL,
  `data` varchar(50) DEFAULT NULL,
  `client_id` int(11) unsigned NOT NULL,
  `time_add` int(11) unsigned NOT NULL,
  `target_id` int(11) unsigned DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `client_id` (`client_id`),
  KEY `time_add` (`time_add`),
  KEY `command` (`command`),
  KEY `target_id` (`target_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `chatlog`
--

CREATE TABLE IF NOT EXISTS `chatlog` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `msg_time` int(10) unsigned NOT NULL,
  `msg_type` enum('ALL','TEAM','PM') DEFAULT NULL,
  `client_id` int(11) unsigned NOT NULL,
  `client_name` varchar(32) DEFAULT NULL,
  `client_team` tinyint(1) NOT NULL,
  `msg` varchar(528) DEFAULT NULL,
  `target_id` int(11) unsigned DEFAULT NULL,
  `target_name` varchar(32) DEFAULT NULL,
  `target_team` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `client` (`client_id`),
  KEY `target` (`target_id`),
  KEY `time_add` (`msg_time`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `flagstats`
--

CREATE TABLE IF NOT EXISTS `flagstats` (
  `mapname` varchar(255) NOT NULL,
  `most_capture_client` int(11) unsigned NOT NULL,
  `most_capture_score` int(11) unsigned NOT NULL,
  `most_capture_timeadd` int(11) unsigned NOT NULL,
  `quick_capture_client` int(11) unsigned NOT NULL,
  `quick_capture_score` float(20,2) unsigned NOT NULL,
  `quick_capture_timeadd` int(11) unsigned NOT NULL,
  PRIMARY KEY (`mapname`),
  KEY `most_capture_client` (`most_capture_client`,`quick_capture_client`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `following`
--

CREATE TABLE IF NOT EXISTS `following` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `client_id` int(11) NOT NULL,
  `admin_id` int(11) NOT NULL,
  `time_add` int(11) NOT NULL,
  `reason` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `following_client_id` (`client_id`),
  KEY `following_admin_id` (`admin_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=latin1 ;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `nicks`
--

CREATE TABLE IF NOT EXISTS `nicks` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nickid` int(11) NOT NULL,
  `name` varchar(32) NOT NULL,
  `clientid` int(11) NOT NULL,
  `time_add` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `nicks_nickid` (`nickid`),
  KEY `nicks_clientid` (`clientid`)
) ENGINE=MyISAM  DEFAULT CHARSET=latin1 ;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `plugin_knife_hof`
--

CREATE TABLE IF NOT EXISTS `plugin_knife_hof` (
  `map_name` varchar(255) NOT NULL,
  `playerid` int(11) NOT NULL,
  `score` smallint(6) NOT NULL,
  `time_add` int(11) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`map_name`),
  KEY `playerid` (`playerid`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `plugin_nader_hef`
--

CREATE TABLE IF NOT EXISTS `plugin_nader_hef` (
  `map_name` varchar(255) NOT NULL,
  `playerid` int(11) NOT NULL,
  `score` smallint(6) NOT NULL,
  `time_add` int(11) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`map_name`),
  KEY `playerid` (`playerid`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `referee`
--

CREATE TABLE IF NOT EXISTS `referee` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `client_id` int(11) NOT NULL,
  `admin_id` int(11) NOT NULL,
  `time_add` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `following_client_id` (`client_id`),
  KEY `following_admin_id` (`admin_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci ;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `tb_autoslap`
--

CREATE TABLE IF NOT EXISTS `tb_autoslap` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `client_id` int(11) NOT NULL,
  `admin_id` int(11) NOT NULL,
  `time_add` int(11) NOT NULL,
  `reason` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `autoslap_client_id` (`client_id`),
  KEY `autoslap_time_add` (`time_add`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci ;
