import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { Linkified } from './Linkified';

describe('Linkified', () => {
  it('turns http(s) addresses into safe links and leaves the rest as text', () => {
    const html = renderToStaticMarkup(
      <Linkified text="Fill https://forms.example.test/a?id=1. Then <b>call</b> 01 234 567" />,
    );
    expect(html).toContain(
      '<a href="https://forms.example.test/a?id=1" target="_blank" rel="noopener noreferrer">',
    );
    expect(html).toContain('</a>. Then');
    expect(html).toContain('&lt;b&gt;call&lt;/b&gt;');
  });

  it('never links other schemes', () => {
    const html = renderToStaticMarkup(<Linkified text="javascript:alert(1) and ftp://x.test" />);
    expect(html).not.toContain('<a ');
  });
});
