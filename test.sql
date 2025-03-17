
-- This migration fixes a bug in the i_output table where the pack_weight column was named incorrectly as pack_time.
-- The fix is to rename the column to pack_time and then modify the data type to be TIMESTAMP WITH TIME ZONE.

ALTER TABLE i_output RENAME COLUMN pack_weight TO pack_time;

ALTER COLUMN pack_time SET DATA TYPE TIMESTAMP WITH TIME ZONE USING TO_TIMESTAMP(pack_time);

----------------------------------------------------------------------------------------------

-- Table: public.i_packing

-- DROP TABLE IF EXISTS public.i_packing;

CREATE TABLE IF NOT EXISTS public.i_packing
(
    id integer NOT NULL,
    date date,
    line character varying(10) COLLATE pg_catalog."default",
    model character varying(6) COLLATE pg_catalog."default",
    shift character varying(10) COLLATE pg_catalog."default",
    inner_code character varying(100) COLLATE pg_catalog."default",
    serial character varying(20) COLLATE pg_catalog."default",
    klippel smallint,
    result boolean,
    scan_time timestamp with time zone
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.i_packing
    OWNER to postgres;

----------------------------------------------------------------------------------------------

