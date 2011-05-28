SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;

--
-- Base de datos: `b3`
--

-- --------------------------------------------------------

--
-- Añadir campo IP a `aliases`
--

ALTER TABLE `aliases` ADD COLUMN `ip` VARCHAR( 16 ) NOT NULL default '';
CREATE INDEX `ip` ON `aliases` (`ip`);

-- --------------------------------------------------------

--
-- Añadir indice IP a `clients`
--

CREATE INDEX `ip` ON `clients` (`ip`);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `disabledcmd`
--

CREATE TABLE IF NOT EXISTS `disabledcmd` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cmd` varchar(50) NOT NULL,
  `until` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `cmd` (`cmd`)
) ENGINE=MyISAM  DEFAULT CHARSET=latin1 ;

-- --------------------------------------------------------
