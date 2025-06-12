import { NextRequest, NextResponse } from 'next/server';
import { extractUrlDomain, extractUrlPath } from '@/utils/urlDecoder';

const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8001';
const CACHE_API_ENDPOINT = `${TARGET_SERVER_BASE_URL}/api/wiki_cache`;

function parseRepoUrl(repoUrl: string): { owner: string; repo: string; repo_type: string } | null {
  repoUrl = repoUrl.trim();
  if (!repoUrl) return null;

  const windowsPathRegex = /^[a-zA-Z]:\\/;
  if (windowsPathRegex.test(repoUrl) || repoUrl.startsWith('/')) {
    const parts = repoUrl.split(/[\\/]/).filter(Boolean);
    const repo = parts.pop() || 'local-repo';
    return { owner: 'local', repo, repo_type: 'local' };
  }

  const path = extractUrlPath(repoUrl)?.replace(/\.git$/, '');
  if (!path) return null;
  const segments = path.split('/');
  if (segments.length < 2) return null;
  const repo = segments.pop() || '';
  const owner = segments.pop() || '';
  const domain = extractUrlDomain(repoUrl) || '';
  let repo_type = 'github';
  if (domain.includes('gitlab')) repo_type = 'gitlab';
  else if (domain.includes('bitbucket')) repo_type = 'bitbucket';
  else if (!domain.includes('github')) repo_type = 'web';
  return { owner, repo, repo_type };
}

export async function GET(req: NextRequest) {
  const repoUrl = req.nextUrl.searchParams.get('repo_url');
  if (!repoUrl) {
    return NextResponse.json({ error: 'repo_url query parameter required' }, { status: 400 });
  }
  const parsed = parseRepoUrl(repoUrl);
  if (!parsed) {
    return NextResponse.json({ error: 'Invalid repo_url format' }, { status: 400 });
  }
  const params = new URLSearchParams({
    owner: parsed.owner,
    repo: parsed.repo,
    repo_type: parsed.repo_type,
    language: 'en',
  });
  const response = await fetch(`${CACHE_API_ENDPOINT}?${params}`, { cache: 'no-store' });
  if (!response.ok) {
    const body = await response.text();
    return new NextResponse(body, { status: response.status, statusText: response.statusText });
  }
  const data = await response.json();
  if (!data || !data.wiki_structure) {
    return NextResponse.json({ error: 'Wiki structure not found' }, { status: 404 });
  }
  return NextResponse.json(data.wiki_structure);
}
