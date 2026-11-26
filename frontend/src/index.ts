interface FilterValidResult {
  valid: boolean;
  maps: Array<boolean>;
}

class Filter {
  private entries: Array<string[]>;
  private amount: number;

  constructor(amount: number) {
    this.entries = new Array(amount).fill(undefined).map((_a) => []);
    this.amount = amount;
  }

  add(index: number, value: string): void {
    if (index < 0 || index >= this.amount) {
      throw new Error("Index out of bounds");
    }
    this.entries[index]!.push(value);
  }

  isValid(value: string): FilterValidResult {
    const result: FilterValidResult = {
      valid: false,
      maps: new Array(this.amount).fill(undefined).map((_a) => false),
    };

    if (value == "") {
      result.valid = true;
      return result;
    }

    for (let i = 0; i < this.amount; ++i) {
      inner: for (const entry of this.entries[i]!) {
        if (entry.includes(value)) {
          result.valid = true;
          result.maps[i] = true;
          break inner;
        }
      }
    }

    return result;
  }
}

interface FilterList {
  filters: Array<Filter>;
}

function getRows(): NodeListOf<HTMLTableRowElement> {
  return document.querySelectorAll<HTMLTableRowElement>(
    "#projects tbody tr.table-entry",
  );
}

function getFilterList(): FilterList {
  const rows = getRows();
  const list: FilterList = {
    filters: new Array(rows.length).fill(undefined).map((_a) => new Filter(0)),
  };

  rows.forEach((row, idx) => {
    list.filters[idx] = new Filter(4);

    const rowData = Array.from(
      row.querySelectorAll<HTMLTableCellElement>("td"),
    );

    if (rowData.length != 4) {
      throw new Error("Invalid row");
    }

    for (let i = 0; i < 4; ++i) {
      const children: Array<ChildNode> = [rowData[i]!];

      while (children.length != 0) {
        const child = children.pop()!;

        if (child.nodeType == Node.TEXT_NODE) {
          continue;
        }

        if (child.nodeType == Node.ELEMENT_NODE) {
          if (child instanceof HTMLElement) {
            const filter_data = child.attributes.getNamedItem("filter-data");

            if (filter_data != null) {
              list.filters[idx].add(i, filter_data.value);
            }
          }
        }

        children.push(...Array.from(child.childNodes));
      }
    }
  });

  return list;
}

function getAttribute(name: string, value: string): Attr {
  const attr = document.createAttribute(name);
  attr.value = value;

  return attr;
}

function searchChanged(
  filterList: FilterList,
): (this: HTMLInputElement) => void {
  return function (this: HTMLInputElement): void {
    const filter = this.value.toLowerCase();

    const rows = getRows();

    let shown = 0;

    rows.forEach((row, idx) => {
      const filters = filterList.filters[idx]!;

      const validResult = filters.isValid(filter);

      if (validResult.valid) {
        shown++;
        row.style.display = "";

        const rowData = Array.from(
          row.querySelectorAll<HTMLTableCellElement>("td"),
        );

        if (rowData.length != 4) {
          throw new Error("Invalid row");
        }

        rowData.forEach((rowData, idx) => {
          if (validResult.maps[idx]) {
            rowData.attributes.setNamedItem(getAttribute("filter", "on"));
          } else {
            rowData.attributes.setNamedItem(getAttribute("filter", "off"));
          }
        });
      } else {
        row.style.display = "none";
      }
    });

    const noElementsFound = document.querySelector<HTMLElement>(
      "#projects tbody tr.no-entries",
    );
    if (noElementsFound) {
      if (shown == 0) {
        noElementsFound.style.display = "";
      } else {
        noElementsFound.style.display = "none";
      }
    }
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
