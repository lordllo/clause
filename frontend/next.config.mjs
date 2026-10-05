/** Static export is opt-in for the single-container hosted demo. */
export default { ...(process.env.CLAUSE_STATIC_EXPORT === 'true' ? {output: 'export'} : {}) };
