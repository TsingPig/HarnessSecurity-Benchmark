INSERT INTO stations VALUES ('river',12,9),('market',10,3),('park',8,5),('library',6,1),('square',10,6),('campus',9,4);
INSERT INTO movements VALUES
  (1,'river','ride',1),(2,'market','return',1),(3,'river','ride',1),
  (4,'library','return',1),(5,'library','ride',1),
  (6,'square','ride',1),(7,'campus','ride',1),(8,'square','return',1),
  (9,'park','return',1),(10,'campus','ride',1),(11,'square','return',1),
  (12,'park','ride',1);
INSERT INTO holds VALUES ('river-1','river',1),('park-1','park',1),('park-2','park',1),('square-1','square',1),('campus-1','campus',1),('market-old','market',0);
INSERT INTO demand VALUES ('river',2,1),('market',8,3),('park',1,1),('library',5,2),('square',3,1),('campus',4,2);
INSERT INTO lanes VALUES ('river','market',5),('park','library',3),('square','campus',2);
