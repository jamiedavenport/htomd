export const SPACE = /\p{White_Space}+/gu;

export class Node {
  children: (Node | string)[] = [];
  constructor(
    public tag: string,
    public attrs: Map<string, string> = new Map(),
    public parent: Node | null = null,
  ) {}
}

export function* walk(root: Node): Generator<Node> {
  const stack = [root];
  while (stack.length) {
    const node = stack.pop()!;
    yield node;
    for (let index = node.children.length - 1; index >= 0; index--) {
      const child = node.children[index];
      if (child instanceof Node) {
        stack.push(child);
      }
    }
  }
}

export function* postorder(root: Node, leafTags: ReadonlySet<string> = new Set()): Generator<Node> {
  const stack: [Node, boolean][] = [[root, false]];
  while (stack.length) {
    const [node, visited] = stack.pop()!;
    if (visited || leafTags.has(node.tag)) {
      yield node;
      continue;
    }
    stack.push([node, true]);
    for (let index = node.children.length - 1; index >= 0; index--) {
      const child = node.children[index];
      if (child instanceof Node) {
        stack.push([child, false]);
      }
    }
  }
}

export function textContent(root: Node, normalize = true): string {
  const pieces: string[] = [];
  const stack: (Node | string)[] = [root];
  while (stack.length) {
    const item = stack.pop()!;
    if (typeof item === "string") {
      pieces.push(item);
    } else {
      for (let index = item.children.length - 1; index >= 0; index--) {
        stack.push(item.children[index]!);
      }
    }
  }
  const value = pieces.join("");
  return normalize ? value.replace(SPACE, " ").trim() : value;
}

export function elements(node: Node): Node[] {
  return node.children.filter((child): child is Node => child instanceof Node);
}
