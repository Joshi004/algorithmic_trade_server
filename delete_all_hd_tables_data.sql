DELIMITER $$

CREATE PROCEDURE DeleteData()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE a CHAR(64);
    DECLARE cur CURSOR FOR
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'ats_db'
        AND table_name LIKE 'hd__%';
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    OPEN cur;
    read_loop: LOOP
        FETCH cur INTO a;

        IF done THEN
            LEAVE read_loop;
        END IF;

        SET @s = CONCAT('DELETE FROM ', a);
        PREPARE stmt FROM @s;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END LOOP;
    CLOSE cur;
END$$
DELIMITER ;

CALL DeleteData();
