# Browser Console Extraction Script

Paste into the browser console on any recipe page with `application/ld+json` structured data (NYT Cooking, Serious Eats, etc.). Outputs markdown in the household recipe format, logs it, and copies it to the clipboard.

```javascript
function parseDuration(iso) {
  if (!iso) return null;
  const m = iso.match(/PT(?:(\d+)H)?(?:(\d+)M)?/);
  if (!m) return null;
  const h = parseInt(m[1] || 0), min = parseInt(m[2] || 0);
  if (h && min) return `${h}hr ${min}min`;
  if (h) return `${h}hr`;
  if (min) return `${min}min`;
  return null;
}

const recipe = Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
  .map(s => { try { return JSON.parse(s.textContent); } catch { return null; } })
  .find(d => d && d['@type'] === 'Recipe');

const yieldRaw = Array.isArray(recipe.recipeYield) ? recipe.recipeYield[0] : recipe.recipeYield;
const prep = parseDuration(recipe.prepTime);
const cook = parseDuration(recipe.cookTime);
const total = parseDuration(recipe.totalTime);

const meta = [
  `**Servings:** ${yieldRaw ?? '?'}`,
  prep  ? `**Prep:** ${prep}`   : null,
  cook  ? `**Cook:** ${cook}`   : null,
  total ? `**Total:** ${total}` : null,
].filter(Boolean).join(' | ');

const ingredients = recipe.recipeIngredient.map(i => `- ${i}`).join('\n');

const instructions = recipe.recipeInstructions
  .map((s, i) => `${i + 1}. ${s.text}`)
  .join('\n');

const md = [
  `# ${recipe.name}`,
  ``,
  meta,
  ``,
  `> Source: ${window.location.href}`,
  ``,
  `## Ingredients`,
  ``,
  ingredients,
  ``,
  `## Instructions`,
  ``,
  instructions,
].join('\n');

console.log(md);
copy(md);
```
