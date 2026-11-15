import { ConceptView } from '@/components/explore/ConceptView';

function decode(s: string) {
  try {
    return decodeURIComponent(s);
  } catch {
    return s;
  }
}

export default async function ConceptPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ConceptView id={decode(id)} />;
}
