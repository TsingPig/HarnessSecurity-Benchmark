function assessCase({ transcript, tags, reportReason, appealText }) {
  // Starter bug: ignores transcript and appeal context.
  const text = `${tags} ${reportReason}`.toLowerCase();
  const high = text.includes('doxx');
  return { risk: high ? 'high' : 'low', finding: high ? 'suspended' : 'cleared', evidence: [] };
}
module.exports = { assessCase };
