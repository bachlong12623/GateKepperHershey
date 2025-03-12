
-- This migration fixes a bug in the i_output table where the pack_weight column was named incorrectly as pack_time.
-- The fix is to rename the column to pack_time and then modify the data type to be TIMESTAMP WITH TIME ZONE.

ALTER TABLE i_output RENAME COLUMN pack_weight TO pack_time;

ALTER COLUMN pack_time SET DATA TYPE TIMESTAMP WITH TIME ZONE USING TO_TIMESTAMP(pack_time);

----------------------------------------------------------------------------------------------