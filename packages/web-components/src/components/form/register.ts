/**
 * Registers every element in the recursive form family.
 *
 * `cofy-any-form` mounts the rest by tag name at runtime (so it never has to import them
 * directly, which would be circular - each container imports `cofy-any-form` back), so nothing
 * else pulls them in as a side effect. Importing this file once is what makes the whole family
 * available.
 */
import "./cofy-any-form.js";
import "./cofy-object-form.js";
import "./cofy-list-form.js";
import "./cofy-union-form.js";
import "./cofy-string-form.js";
import "./cofy-secret-form.js";
import "./cofy-number-form.js";
import "./cofy-boolean-form.js";
import "./cofy-enum-form.js";
import "./cofy-const-form.js";
import "./cofy-unknown-form.js";
