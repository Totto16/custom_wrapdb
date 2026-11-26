class Filter {
  private entries: string[];

  constructor() {
    this.entries = [];
  }

  add(value: string): void {
    this.entries.push(value);
  }

  isValid(value: string): boolean {
    console.log(this.entries);
    for (const entry of this.entries) {
      if (entry.includes(value)) {
        return true;
      }
    }

    return false;
  }
}

interface FilterList {
  filters: Array<Filter>;
}

function getRows(): NodeListOf<HTMLElement> {
  return document.querySelectorAll<HTMLElement>("#projects tbody tr");
}

function getFilterList(): FilterList {
  const rows = getRows();
  const list: FilterList = {
    filters: new Array(rows.length).map((_a) => new Filter()),
  };

  rows.forEach((row, idx) => {
    list.filters[idx] = new Filter();

    const children: Array<ChildNode> = [row];

    while (children.length != 0) {
      const child = children.pop()!;

      if (child.nodeType == Node.TEXT_NODE) {
        continue;
      }

      if (child.nodeType == Node.ELEMENT_NODE) {
        if (child instanceof HTMLElement) {
          const filter_data = child.attributes.getNamedItem("filter-data");

          if (filter_data != null) {
            list.filters[idx].add(filter_data.value);
          }
        }
      }

      children.push(...Array.from(child.childNodes));
    }
  });

  return list;
}

function searchChanged(
  filterList: FilterList,
): (this: HTMLInputElement) => void {
  return function (this: HTMLInputElement): void {
    const filter = this.value.toLowerCase();

    const rows = getRows();

    rows.forEach((row, idx) => {
      const filters = filterList.filters[idx]!;

      if (filters.isValid(filter)) {
        row.style.display = "";
      } else {
        row.style.display = "none";
      }
    });
  };
}

async function main(): Promise<void> {
  const searchElem = document.getElementById("search");

  if (!searchElem) {
    throw new Error("Search element not found");
  }

  const filterList = getFilterList();

  searchElem.addEventListener("input", searchChanged(filterList));
}

void main();
