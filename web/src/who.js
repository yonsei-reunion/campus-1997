// The cast's ids are numbers: p01 .. p17, in the order blender/characters.py PEOPLE lists them (the order of the
// faces' cells too).  What a number does not tell is kept here: who is a woman (the women's rig: 1.61 m at the eyes'
// reckoning where the men are 1.73), and who is not a student.
export const WOMEN = new Set(['p09', 'p10', 'p11', 'p12', 'p13', 'p14', 'p15', 'p17']);
export const PROFESSOR = 'p07', STAFF = ['p08', 'p14'];
export const isWoman = (id) => WOMEN.has(String(id));
export const kindOf = (id) => (id === PROFESSOR ? 'prof' : STAFF.includes(id) ? 'staff' : 'student');
// the height a model stands (m, before a look's or a hero's scale)
export const tallOf = (id) => (isWoman(id) ? 1.61 : 1.73);
